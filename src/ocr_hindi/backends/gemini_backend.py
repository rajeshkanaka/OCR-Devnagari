"""Gemini 2.0 Flash Vision API backend - Optimized for OCR.

Uses gemini-2.0-flash model for faithful transcription:

- No autocorrection of mantras (unlike Gemini 2.5+/3.x)
- media_resolution: "high" for optimal PDF/image processing
- Token tracking for cost calculation

Pricing (per 1M tokens):

- Input: $0.15 (standard) / $0.075 (batch)
- Output: $0.60 (standard) / $0.30 (batch)
"""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass

from PIL import Image

from ..prompts import OCR_PROMPT
from .base import BackendConfig, OCRBackend, OCRResult

logger = logging.getLogger(__name__)

# Gemini 2.0 Flash pricing (per 1M tokens, standard API)
_INPUT_COST_PER_MILLION = 0.15
_OUTPUT_COST_PER_MILLION = 0.60


@dataclass
class TokenUsage:
    """Track token usage for cost calculation."""

    input_tokens: int = 0
    output_tokens: int = 0

    INPUT_COST_PER_MILLION: float = _INPUT_COST_PER_MILLION
    OUTPUT_COST_PER_MILLION: float = _OUTPUT_COST_PER_MILLION

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add token counts from an API call."""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def merge(self, other: TokenUsage) -> None:
        """Merge another TokenUsage into this one."""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used."""
        return self.input_tokens + self.output_tokens

    @property
    def input_cost(self) -> float:
        """Cost for input tokens in USD."""
        return (self.input_tokens / 1_000_000) * self.INPUT_COST_PER_MILLION

    @property
    def output_cost(self) -> float:
        """Cost for output tokens in USD."""
        return (self.output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MILLION

    @property
    def total_cost(self) -> float:
        """Total cost in USD."""
        return self.input_cost + self.output_cost

    def format_cost(self) -> str:
        """Format cost as readable string."""
        return f"${self.total_cost:.4f}"

    def format_detailed(self) -> str:
        """Format detailed breakdown."""
        return (
            f"Tokens: {self.input_tokens:,} input + "
            f"{self.output_tokens:,} output = {self.total_tokens:,} total\n"
            f"Cost: ${self.input_cost:.4f} (input) + "
            f"${self.output_cost:.4f} (output) = ${self.total_cost:.4f} total"
        )

    def reset(self) -> None:
        """Reset counters."""
        self.input_tokens = 0
        self.output_tokens = 0


class GeminiBackend(OCRBackend):
    """Gemini 2.0 Flash Vision API backend - Optimized for OCR.

    Model: gemini-2.0-flash
    Cost: ~$0.15/$0.60 per 1M tokens (input/output)

    Advantages for sacred text OCR:

    - Faithful transcription (no autocorrection of mantras)
    - media_resolution: "high" for maximum quality
    - Response validation: rejects empty or error responses
    - 75% cheaper than Gemini 3 Flash
    """

    _ERROR_PATTERNS = (
        "cannot process",
        "unable to",
        "error:",
        "i'm sorry",
        "i cannot",
        "i can't",
        "cannot extract",
        "unable to extract",
        "no text found",
        "image is not clear",
        "cannot read",
        "cannot see",
        "not able to",
    )

    _MIN_VALID_LENGTH = 20

    def __init__(
        self,
        config: BackendConfig | None = None,
        model: str = "gemini-2.0-flash",
        rate_limit: int = 60,
        max_retries: int = 3,
        thinking_level: str = "low",
    ) -> None:
        super().__init__(config)
        self.model = model
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.thinking_level = thinking_level
        self.client = None
        self._last_request_time = 0.0
        self._min_request_interval = 60.0 / rate_limit
        self.token_usage = TokenUsage()

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_free(self) -> bool:
        return False

    @property
    def cost_per_1000_pages(self) -> float:
        """Estimate based on typical page: ~1000 input, ~500 output tokens."""
        avg_input_per_page = 1000
        avg_output_per_page = 500
        input_cost = (
            avg_input_per_page * 1000 / 1_000_000
        ) * _INPUT_COST_PER_MILLION
        output_cost = (
            avg_output_per_page * 1000 / 1_000_000
        ) * _OUTPUT_COST_PER_MILLION
        return input_cost + output_cost

    def initialize(self) -> tuple[bool, str]:
        """Initialize Gemini client with auth validation."""
        try:
            from google import genai
            from google.genai import types

            use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in (
                "1",
                "true",
                "yes",
            )
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

            gen_config = self._build_gen_config(types)

            if use_vertex and project:
                self.client = genai.Client(
                    vertexai=True, project=project, location=location
                )
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="Say 'OK'",
                    config=gen_config,
                )
                if response.text:
                    self._initialized = True
                    return True, f"Vertex AI: Project={project}, Model={self.model}"

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="Say 'OK'",
                    config=gen_config,
                )
                if response.text:
                    self._initialized = True
                    return True, f"API Key, Model={self.model}"

            return False, "No valid authentication found"

        except Exception as exc:
            return False, f"Initialization failed: {exc}"

    def _build_gen_config(self, types_module, *, include_media_res: bool = False):
        """Build GenerateContentConfig with model-appropriate settings.

        Args:
            types_module: The google.genai.types module.
            include_media_res: Whether to include media_resolution (for OCR).

        Returns:
            Config object, or None if no special config needed.
        """
        config_kwargs: dict = {}
        if "gemini-3" in self.model or "gemini-2.5" in self.model:
            config_kwargs["thinking_config"] = types_module.ThinkingConfig(
                thinking_level=self.thinking_level
            )
        if include_media_res:
            config_kwargs[
                "media_resolution"
            ] = types_module.MediaResolution.MEDIA_RESOLUTION_HIGH

        if config_kwargs:
            return types_module.GenerateContentConfig(**config_kwargs)
        return None

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _extract_token_usage(self, response) -> tuple[int, int]:
        """Extract token usage from API response.

        Args:
            response: The Gemini API response object.

        Returns:
            Tuple of (input_tokens, output_tokens).
        """
        try:
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                return input_tokens, output_tokens

            # Fallback: estimate from content
            input_tokens = 1000  # Image estimate
            output_tokens = len(response.text) // 4 if response.text else 0
            return input_tokens, output_tokens
        except Exception:
            return 1000, 500  # Default estimates

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process image with Gemini Vision API.

        Uses high media resolution for best OCR quality and tracks
        token usage for cost calculation.

        Args:
            image: PIL Image of the page.
            page_num: Page number for reference.

        Returns:
            OCRResult with extracted text.
        """
        if not self._initialized or not self.client:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Backend not initialized",
                backend_used=self.name,
            )

        from google.genai import types

        start_time = time.time()

        for attempt in range(self.max_retries):
            try:
                self._enforce_rate_limit()

                gen_config = self._build_gen_config(types, include_media_res=True)

                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[image, OCR_PROMPT],
                    config=gen_config,
                )

                text = response.text.strip() if response.text else ""
                duration = time.time() - start_time

                input_tokens, output_tokens = self._extract_token_usage(response)
                self.token_usage.add(input_tokens, output_tokens)

                is_valid, validation_error = self._validate_response(text, page_num)
                if not is_valid:
                    if attempt < self.max_retries - 1:
                        continue
                    return OCRResult(
                        page_num=page_num,
                        text="",
                        success=False,
                        error=f"Validation failed: {validation_error}",
                        duration=duration,
                        backend_used=self.name,
                    )

                return OCRResult(
                    page_num=page_num,
                    text=text,
                    success=True,
                    confidence=0.95,
                    duration=duration,
                    backend_used=self.name,
                    needs_verification=self.contains_mantra(text),
                )

            except Exception as exc:
                error_msg = str(exc)
                logger.warning(
                    "Page %d, attempt %d/%d: %s",
                    page_num,
                    attempt + 1,
                    self.max_retries,
                    error_msg,
                )

                if "429" in error_msg or "quota" in error_msg.lower():
                    delay = 2.0 * (2**attempt) * 2
                    time.sleep(delay)
                elif attempt < self.max_retries - 1:
                    delay = 2.0 * (2**attempt)
                    time.sleep(delay)

        duration = time.time() - start_time
        return OCRResult(
            page_num=page_num,
            text="",
            success=False,
            error=f"Failed after {self.max_retries} attempts",
            duration=duration,
            backend_used=self.name,
        )

    def get_token_usage(self) -> TokenUsage:
        """Get current token usage."""
        return self.token_usage

    def get_cost(self) -> float:
        """Get total cost in USD."""
        return self.token_usage.total_cost

    def print_cost_summary(self) -> None:
        """Print detailed cost summary via logging."""
        logger.info(
            "Gemini API Cost — Model: %s, Thinking: %s\n    %s",
            self.model,
            self.thinking_level,
            self.token_usage.format_detailed(),
        )

    def reset_token_usage(self) -> None:
        """Reset token tracking."""
        self.token_usage.reset()

    def _validate_response(self, text: str, page_num: int) -> tuple[bool, str]:
        """Validate OCR response before accepting it.

        Checks for empty responses, error messages disguised as content,
        and invalid patterns indicating OCR failure.

        Args:
            text: The OCR response text.
            page_num: Page number for logging.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if not text or len(text.strip()) < self._MIN_VALID_LENGTH:
            return (
                False,
                f"Response too short ({len(text.strip())} chars, "
                f"min {self._MIN_VALID_LENGTH})",
            )

        text_lower = text.lower()[:300]
        for pattern in self._ERROR_PATTERNS:
            if pattern in text_lower:
                return False, f"Response contains error pattern: '{pattern}'"

        stripped = text.strip()
        if not any(c.isalnum() for c in stripped):
            return False, "Response contains no alphanumeric characters"

        return True, ""
