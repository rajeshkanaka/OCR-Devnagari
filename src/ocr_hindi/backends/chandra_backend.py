"""Chandra OCR backend - Vision-language model for multilingual OCR.

FREE - Self-hosted, runs on CPU or GPU.
Supports 90+ languages including Hindi (Devanagari).
Excels at layout preservation, tables, and structured documents.

Model: datalab-to/chandra-ocr-2
Install: pip install 'chandra-ocr[hf]'
"""

from __future__ import annotations

import logging
import re
import time

from PIL import Image

from .base import BackendConfig, OCRBackend, OCRResult

logger = logging.getLogger(__name__)


class ChandraBackend(OCRBackend):
    """Chandra OCR backend for Hindi/Sanskrit OCR.

    Cost: $0 (runs locally, self-hosted)
    Accuracy: Excellent for structured documents (85.9% overall)
    Weakness: Degraded/old scans (49.8%)

    Uses the datalab-to/chandra-ocr-2 model via HuggingFace or vLLM.
    """

    def __init__(
        self,
        config: BackendConfig | None = None,
        method: str = "hf",
        prompt_type: str = "ocr_layout",
        preserve_markdown: bool = False,
    ) -> None:
        super().__init__(config)
        self.method = method
        self.prompt_type = prompt_type
        self.preserve_markdown = preserve_markdown
        self._manager = None

    @property
    def name(self) -> str:
        return "chandra"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def cost_per_1000_pages(self) -> float:
        return 0.0

    def initialize(self) -> tuple[bool, str]:
        """Initialize Chandra InferenceManager."""
        try:
            from chandra.model import InferenceManager
        except ImportError:
            return False, (
                "Chandra OCR not installed. Install with:\n"
                "  pip install 'chandra-ocr[hf]'\n"
                "  # For vLLM (faster batch, requires GPU):\n"
                "  pip install 'chandra-ocr[all]'"
            )

        try:
            self._manager = InferenceManager(method=self.method)
            self._initialized = True
            return True, f"Chandra OCR ready (method={self.method})"
        except Exception as exc:
            return False, f"Failed to initialize Chandra OCR: {exc}"

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process a single image with Chandra OCR."""
        if not self._initialized or self._manager is None:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Backend not initialized",
                backend_used=self.name,
            )

        start_time = time.time()

        try:
            from chandra.model.schema import BatchInputItem

            batch = [BatchInputItem(image=image, prompt_type=self.prompt_type)]
            results = self._manager.generate(batch)
            if not results:
                return OCRResult(
                    page_num=page_num,
                    text="",
                    success=False,
                    error="Chandra returned no results",
                    duration=time.time() - start_time,
                    backend_used=self.name,
                )
            result = results[0]

            raw_text = getattr(result, "markdown", None) or ""
            text = raw_text if self.preserve_markdown else self._strip_markdown(raw_text)

            confidence = self._estimate_confidence(text)

            return OCRResult(
                page_num=page_num,
                text=text,
                success=True,
                confidence=confidence,
                duration=time.time() - start_time,
                backend_used=self.name,
                needs_verification=self.contains_mantra(text),
            )

        except Exception as exc:
            logger.error("Chandra OCR failed on page %d: %s", page_num, exc)
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error=str(exc),
                duration=time.time() - start_time,
                backend_used=self.name,
            )

    @staticmethod
    def _strip_markdown(text: str) -> str:
        """Strip Markdown formatting to produce plain text."""
        text = re.sub(r"^#{1,6}\s+", "", text, flags=re.MULTILINE)
        text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)
        text = re.sub(r"\*(.+?)\*", r"\1", text)
        text = re.sub(r"^---+$", "", text, flags=re.MULTILINE)
        text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """Estimate OCR confidence from text quality heuristics."""
        if not text:
            return 0.0

        issues = 0

        if re.search(r"[^\w\s]{5,}", text):
            issues += 1
        if len(text) < 50:
            issues += 1

        letters = sum(1 for c in text if c.isalpha())
        if letters < len(text) * 0.3:
            issues += 1

        # Devanagari-specific: flag if some Devanagari present but very little
        devanagari = sum(1 for c in text if "\u0900" <= c <= "\u097f")
        if devanagari > 0 and letters > 0 and devanagari < letters * 0.1:
            issues += 1

        return max(0.4, 1.0 - (issues * 0.15))

    def cleanup(self) -> None:
        """Free model memory and GPU resources."""
        self._initialized = False
        if self._manager is not None:
            del self._manager
            self._manager = None
            try:
                import torch

                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
                elif (
                    hasattr(torch.backends, "mps")
                    and torch.backends.mps.is_available()
                    and hasattr(torch, "mps")
                    and hasattr(torch.mps, "empty_cache")
                ):
                    torch.mps.empty_cache()
            except ImportError:
                pass
