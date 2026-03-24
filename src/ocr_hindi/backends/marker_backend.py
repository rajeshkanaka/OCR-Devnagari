"""Marker backend - Open-source PDF to Markdown conversion.

FREE - Runs locally on CPU/GPU/MPS.
Highly accurate for books and manuscripts.
Best option for bulk processing with excellent Markdown output.
"""

from __future__ import annotations

import logging
import re
import time
from pathlib import Path

from PIL import Image

from .base import BackendConfig, OCRBackend, OCRResult

logger = logging.getLogger(__name__)


class MarkerBackend(OCRBackend):
    """Marker PDF to Markdown backend.

    Cost: $0 (runs locally)
    Accuracy: Very good for structured documents

    Note: Marker works on entire PDFs, not individual images.
    For page-by-page processing, it converts then extracts.
    """

    def __init__(
        self,
        config: BackendConfig | None = None,
        use_gpu: bool = True,
        batch_size: int = 10,
    ) -> None:
        super().__init__(config)
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self._marker_available = False
        self._model_dict = None
        self._converter = None

    @property
    def name(self) -> str:
        return "marker"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def cost_per_1000_pages(self) -> float:
        return 0.0

    def initialize(self) -> tuple[bool, str]:
        """Check if Marker is available and load models."""
        try:
            from marker.converters.pdf import PdfConverter
            from marker.models import create_model_dict
        except ImportError:
            return False, (
                "Marker not installed. Install with:\n"
                "  pip install marker-pdf\n"
                "  # For GPU support:\n"
                "  pip install marker-pdf[gpu]"
            )

        try:
            self._model_dict = create_model_dict()
            self._converter = PdfConverter(artifact_dict=self._model_dict)
            self._marker_available = True
            self._initialized = True
            device_info = "GPU" if self.use_gpu else "CPU"
            return True, f"Marker ready ({device_info})"
        except Exception as exc:
            return False, f"Failed to load Marker models: {exc}"

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process a single image with Marker.

        Marker is optimized for PDF processing, not individual images.
        For single images, saves to a temp PDF and processes.

        Args:
            image: PIL Image of the page.
            page_num: Page number for reference.

        Returns:
            OCRResult with extracted text.
        """
        if not self._initialized:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Backend not initialized",
                backend_used=self.name,
            )

        start_time = time.time()

        try:
            import tempfile

            from marker.output import text_from_rendered

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(tmp.name, "PDF")
                tmp_path = Path(tmp.name)

            try:
                rendered = self._converter(str(tmp_path))
                text = text_from_rendered(rendered)

                return OCRResult(
                    page_num=page_num,
                    text=text.strip(),
                    success=True,
                    confidence=self._estimate_confidence(text),
                    duration=time.time() - start_time,
                    backend_used=self.name,
                    needs_verification=self.contains_mantra(text),
                )
            finally:
                tmp_path.unlink(missing_ok=True)

        except Exception as exc:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error=str(exc),
                duration=time.time() - start_time,
                backend_used=self.name,
            )

    def process_pdf(self, pdf_path: Path) -> tuple[dict[int, str], float]:
        """Process entire PDF at once (more efficient for Marker).

        Args:
            pdf_path: Path to PDF file.

        Returns:
            Tuple of (page_num->text mapping, total_duration).

        Raises:
            RuntimeError: If backend not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")

        from marker.output import text_from_rendered

        start_time = time.time()
        rendered = self._converter(str(pdf_path))
        full_text = text_from_rendered(rendered)
        pages = self._split_by_pages(full_text)
        return pages, time.time() - start_time

    @staticmethod
    def _split_by_pages(text: str) -> dict[int, str]:
        """Split combined text by page markers.

        Args:
            text: Combined text output from Marker.

        Returns:
            Dict mapping page numbers to text content.
        """
        pages: dict[int, str] = {}
        page_pattern = (
            r"(?:^|\n)(?:---\s*)?(?:Page|PAGE|page)\s*(\d+)(?:\s*---)?(?:\n|$)"
        )
        matches = list(re.finditer(page_pattern, text))

        if matches:
            for i, match in enumerate(matches):
                page_num = int(match.group(1))
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                pages[page_num] = text[start:end].strip()
        else:
            pages[1] = text.strip()

        return pages

    @staticmethod
    def _estimate_confidence(text: str) -> float:
        """Estimate OCR confidence based on text quality.

        Args:
            text: Extracted text to evaluate.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
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

        return max(0.5, 1.0 - (issues * 0.15))

    def cleanup(self) -> None:
        """Free model memory."""
        if self._model_dict is not None:
            del self._model_dict
            self._model_dict = None
        if self._converter is not None:
            del self._converter
            self._converter = None
