"""
Gemini 3 Flash Vision API backend - Optimized for OCR.

Uses the latest gemini-3-flash-preview model with:
- thinking_level: "low" for fast OCR (minimal reasoning needed)
- media_resolution: "medium" for optimal PDF/image processing
- Token tracking for cost calculation

Pricing (per 1M tokens):
- Input: $0.50
- Output: $3.00
"""

import os
import time
from dataclasses import dataclass, field
from typing import Optional
from PIL import Image
from termcolor import colored

from .base import OCRBackend, OCRResult, BackendConfig
from ..prompts import OCR_PROMPT


@dataclass
class TokenUsage:
    """Track token usage for cost calculation"""

    input_tokens: int = 0
    output_tokens: int = 0

    # Gemini 3 Flash pricing (per 1M tokens)
    INPUT_COST_PER_MILLION: float = 0.50  # $0.50 per 1M input tokens
    OUTPUT_COST_PER_MILLION: float = 3.00  # $3.00 per 1M output tokens

    def add(self, input_tokens: int, output_tokens: int) -> None:
        """Add token counts"""
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens

    def merge(self, other: "TokenUsage") -> None:
        """Merge another TokenUsage into this one"""
        self.input_tokens += other.input_tokens
        self.output_tokens += other.output_tokens

    @property
    def total_tokens(self) -> int:
        """Total tokens used"""
        return self.input_tokens + self.output_tokens

    @property
    def input_cost(self) -> float:
        """Cost for input tokens in USD"""
        return (self.input_tokens / 1_000_000) * self.INPUT_COST_PER_MILLION

    @property
    def output_cost(self) -> float:
        """Cost for output tokens in USD"""
        return (self.output_tokens / 1_000_000) * self.OUTPUT_COST_PER_MILLION

    @property
    def total_cost(self) -> float:
        """Total cost in USD"""
        return self.input_cost + self.output_cost

    def format_cost(self) -> str:
        """Format cost as readable string"""
        return f"${self.total_cost:.4f}"

    def format_detailed(self) -> str:
        """Format detailed breakdown"""
        return (
            f"Tokens: {self.input_tokens:,} input + {self.output_tokens:,} output = {self.total_tokens:,} total\n"
            f"Cost: ${self.input_cost:.4f} (input) + ${self.output_cost:.4f} (output) = ${self.total_cost:.4f} total"
        )

    def reset(self) -> None:
        """Reset counters"""
        self.input_tokens = 0
        self.output_tokens = 0


class GeminiBackend(OCRBackend):
    """
    Gemini 3 Flash Vision API backend - Optimized for OCR.

    Model: gemini-3-flash-preview
    Cost: ~$0.50/$3.00 per 1M tokens (input/output)

    Optimizations for OCR:
    - thinking_level: "low" - Fast responses, minimal reasoning
    - media_resolution: "high" - Maximum quality for OCR accuracy
    - temperature: 1.0 (default, as recommended by Gemini 3)
    - Response validation: Rejects empty or error responses
    """

    # Error patterns that indicate OCR failure (not actual content)
    ERROR_PATTERNS = [
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
    ]

    # Minimum characters for valid OCR result
    MIN_VALID_LENGTH = 20

    def __init__(
        self,
        config: Optional[BackendConfig] = None,
        model: str = "gemini-3-flash-preview",
        rate_limit: int = 60,  # Gemini 3 Flash has higher rate limits
        max_retries: int = 3,
        thinking_level: str = "low",  # "minimal", "low", "medium", "high"
    ):
        super().__init__(config)
        self.model = model
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.thinking_level = thinking_level
        self.client = None
        self._last_request_time = 0.0
        self._min_request_interval = 60.0 / rate_limit

        # Token tracking
        self.token_usage = TokenUsage()

    @property
    def name(self) -> str:
        return "gemini"

    @property
    def is_free(self) -> bool:
        return False

    @property
    def cost_per_1000_pages(self) -> float:
        # Estimate based on typical page: ~1000 input tokens (image), ~500 output tokens
        avg_input_per_page = 1000
        avg_output_per_page = 500

        input_cost = (
            avg_input_per_page * 1000 / 1_000_000
        ) * TokenUsage.INPUT_COST_PER_MILLION
        output_cost = (
            avg_output_per_page * 1000 / 1_000_000
        ) * TokenUsage.OUTPUT_COST_PER_MILLION

        return input_cost + output_cost  # ~$2 per 1000 pages

    def initialize(self) -> tuple[bool, str]:
        """Initialize Gemini client with auth validation"""
        try:
            from google import genai
            from google.genai import types

            # Check for Vertex AI
            use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in (
                "1",
                "true",
                "yes",
            )
            project = os.getenv("GOOGLE_CLOUD_PROJECT")

            # Gemini 3 Flash requires 'global' location - force it
            # Older models can use global or other regions
            if "gemini-3" in self.model:
                location = "global"  # Required for Gemini 3 models
            else:
                location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

            if use_vertex and project:
                self.client = genai.Client(
                    vertexai=True, project=project, location=location
                )
                # Test connection with thinking_level
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="Say 'OK'",
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level=self.thinking_level
                        )
                    ),
                )
                if response.text:
                    self._initialized = True
                    return True, f"Vertex AI: Project={project}, Model={self.model}"

            # Try API key
            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                response = self.client.models.generate_content(
                    model=self.model,
                    contents="Say 'OK'",
                    config=types.GenerateContentConfig(
                        thinking_config=types.ThinkingConfig(
                            thinking_level=self.thinking_level
                        )
                    ),
                )
                if response.text:
                    self._initialized = True
                    return True, f"API Key, Model={self.model}"

            return False, "No valid authentication found"

        except Exception as e:
            return False, f"Initialization failed: {str(e)}"

    def _rate_limit(self) -> None:
        """Enforce rate limiting"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _extract_token_usage(self, response) -> tuple[int, int]:
        """Extract token usage from API response"""
        try:
            # Try to get usage metadata from response
            if hasattr(response, "usage_metadata"):
                usage = response.usage_metadata
                input_tokens = getattr(usage, "prompt_token_count", 0) or 0
                output_tokens = getattr(usage, "candidates_token_count", 0) or 0
                return input_tokens, output_tokens

            # Fallback: estimate from content
            # Images typically use ~1000 tokens, text varies
            input_tokens = 1000  # Estimate for image
            output_tokens = (
                len(response.text) // 4 if response.text else 0
            )  # ~4 chars per token
            return input_tokens, output_tokens

        except Exception:
            return 1000, 500  # Default estimates

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """
        Process image with Gemini 3 Flash Vision API.

        Optimizations:
        - thinking_level: "low" for fast OCR
        - Tracks token usage for cost calculation
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
                self._rate_limit()

                # Use Gemini 3 optimized config with high media resolution for OCR
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=[image, OCR_PROMPT],
                    config=types.GenerateContentConfig(
                        # Gemini 3 Flash specific settings
                        thinking_config=types.ThinkingConfig(
                            thinking_level=self.thinking_level  # "low" for fast OCR
                        ),
                        # HIGH resolution for best OCR quality (1120 tokens per image)
                        # This provides more detail for accurate text extraction
                        media_resolution=types.MediaResolution.MEDIA_RESOLUTION_HIGH,
                        # Keep temperature at default 1.0 as recommended
                    ),
                )

                text = response.text.strip() if response.text else ""
                duration = time.time() - start_time

                # Track token usage
                input_tokens, output_tokens = self._extract_token_usage(response)
                self.token_usage.add(input_tokens, output_tokens)

                # Validate response before accepting
                is_valid, validation_error = self._validate_response(text, page_num)
                if not is_valid:
                    # Invalid response - retry or fail
                    if attempt < self.max_retries - 1:
                        continue  # Retry
                    return OCRResult(
                        page_num=page_num,
                        text="",
                        success=False,
                        error=f"Validation failed: {validation_error}",
                        duration=duration,
                        backend_used=self.name,
                    )

                # Check for mantras
                needs_verification = self._contains_mantra(text)

                return OCRResult(
                    page_num=page_num,
                    text=text,
                    success=True,
                    confidence=0.95,  # Gemini 3 Flash is high confidence
                    duration=duration,
                    backend_used=self.name,
                    needs_verification=needs_verification,
                )

            except Exception as e:
                error_msg = str(e)

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
        """Get current token usage"""
        return self.token_usage

    def get_cost(self) -> float:
        """Get total cost in USD"""
        return self.token_usage.total_cost

    def print_cost_summary(self) -> None:
        """Print detailed cost summary"""
        print(colored("\n  💰 Gemini API Cost Summary:", "cyan"))
        print(colored(f"    Model: {self.model}", "white"))
        print(colored(f"    Thinking Level: {self.thinking_level}", "white"))
        print(f"    {self.token_usage.format_detailed()}")

    def reset_token_usage(self) -> None:
        """Reset token tracking"""
        self.token_usage.reset()

    def _validate_response(self, text: str, page_num: int) -> tuple[bool, str]:
        """
        Validate OCR response before accepting it.

        Checks for:
        - Empty or too short responses
        - Error messages disguised as content
        - Invalid patterns indicating OCR failure

        Args:
            text: The OCR response text
            page_num: Page number for logging

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check for empty or too short response
        if not text or len(text.strip()) < self.MIN_VALID_LENGTH:
            return (
                False,
                f"Response too short ({len(text.strip())} chars, min {self.MIN_VALID_LENGTH})",
            )

        # Check for error patterns in the first 300 chars (error messages are usually at start)
        text_lower = text.lower()[:300]
        for pattern in self.ERROR_PATTERNS:
            if pattern in text_lower:
                return False, f"Response contains error pattern: '{pattern}'"

        # Check if response is just whitespace or formatting
        stripped = text.strip()
        if not any(c.isalnum() for c in stripped):
            return False, "Response contains no alphanumeric characters"

        return True, ""

    def _contains_mantra(self, text: str) -> bool:
        """Check if text contains mantra patterns"""
        mantra_patterns = [
            "॥",
            "ॐ",
            "स्वाहा",
            "नमः",
            "फट्",
            "हुं",
            "ह्रीं",
            "श्रीं",
            "क्लीं",
            "ऐं",
        ]

        if not self.config.detect_mantras:
            return False

        return any(pattern in text for pattern in mantra_patterns)
