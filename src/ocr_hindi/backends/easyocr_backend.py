"""EasyOCR backend - Open-source OCR with excellent Hindi/Devanagari support.

FREE - Runs locally on CPU/GPU.
Supports 80+ languages including Hindi (hi), Sanskrit transliteration.
"""

from __future__ import annotations

import logging
import time

from PIL import Image

from .base import BackendConfig, OCRBackend, OCRResult

logger = logging.getLogger(__name__)


class EasyOCRBackend(OCRBackend):
    """EasyOCR backend for Hindi/Sanskrit OCR.

    Cost: $0 (runs locally)
    Accuracy: Good for printed Devanagari text

    Languages supported:

    - hi: Hindi
    - en: English (for mixed text)
    - sa: Sanskrit (via Devanagari support)
    """

    def __init__(
        self,
        config: BackendConfig | None = None,
        use_gpu: bool = True,
        languages: list[str] | None = None,
    ) -> None:
        super().__init__(config)
        self.use_gpu = use_gpu
        self.languages = languages or ["hi", "en"]
        self._reader = None

    @property
    def name(self) -> str:
        return "easyocr"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def cost_per_1000_pages(self) -> float:
        return 0.0

    def initialize(self) -> tuple[bool, str]:
        """Initialize EasyOCR reader."""
        try:
            import easyocr
        except ImportError:
            return False, (
                "EasyOCR not installed. Install with:\n"
                "  pip install easyocr\n"
                "  # For GPU support, ensure torch with CUDA is installed"
            )

        import warnings

        warnings.filterwarnings("ignore", message=".*pin_memory.*")
        warnings.filterwarnings("ignore", category=UserWarning, module="torch")

        try:
            self._reader = easyocr.Reader(
                self.languages,
                gpu=self.use_gpu,
                verbose=False,
            )
            self._initialized = True
            device_info = "GPU" if self.use_gpu else "CPU"
            return True, (
                f"EasyOCR ready ({device_info}, "
                f"languages: {', '.join(self.languages)})"
            )
        except Exception as exc:
            return False, f"Failed to load EasyOCR models: {exc}"

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process image with EasyOCR.

        Args:
            image: PIL Image of the page.
            page_num: Page number for reference.

        Returns:
            OCRResult with extracted text and confidence score.
        """
        if not self._initialized or not self._reader:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Backend not initialized",
                backend_used=self.name,
            )

        start_time = time.time()

        try:
            import numpy as np

            image_array = np.array(image)

            results = self._reader.readtext(
                image_array,
                detail=1,
                paragraph=True,
            )

            if not results:
                return OCRResult(
                    page_num=page_num,
                    text="",
                    success=True,
                    confidence=0.0,
                    duration=time.time() - start_time,
                    backend_used=self.name,
                )

            texts = []
            confidences = []

            for item in results:
                if len(item) >= 2:
                    texts.append(item[1])
                    confidences.append(item[2] if len(item) > 2 else 0.8)

            full_text = "\n".join(texts)
            avg_confidence = (
                sum(confidences) / len(confidences) if confidences else 0.5
            )

            return OCRResult(
                page_num=page_num,
                text=full_text,
                success=True,
                confidence=avg_confidence,
                duration=time.time() - start_time,
                backend_used=self.name,
                needs_verification=self.contains_mantra(full_text),
            )

        except Exception as exc:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error=str(exc),
                duration=time.time() - start_time,
                backend_used=self.name,
            )

    def cleanup(self) -> None:
        """Free reader memory."""
        if self._reader is not None:
            del self._reader
            self._reader = None
