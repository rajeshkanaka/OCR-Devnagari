"""Tesseract OCR backend - Google's open-source OCR engine.

FREE - Runs locally.
Supports Hindi (hin) and Sanskrit (san) languages.
Requires tesseract-ocr to be installed on the system.
"""

from __future__ import annotations

import logging
import subprocess
import time

from PIL import Image

from .base import BackendConfig, OCRBackend, OCRResult

logger = logging.getLogger(__name__)

_SUBPROCESS_TIMEOUT = 10


class TesseractBackend(OCRBackend):
    """Tesseract OCR backend.

    Cost: $0 (runs locally)
    Accuracy: Good, may need training for old manuscripts

    System requirements:

    - macOS: ``brew install tesseract tesseract-lang``
    - Ubuntu: ``apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san``
    """

    def __init__(
        self,
        config: BackendConfig | None = None,
        languages: list[str] | None = None,
        oem: int = 3,
        psm: int = 3,
    ) -> None:
        super().__init__(config)
        self.languages = languages or ["hin", "san", "eng"]
        self.oem = oem
        self.psm = psm
        self._tesseract = None

    @property
    def name(self) -> str:
        return "tesseract"

    @property
    def is_free(self) -> bool:
        return True

    @property
    def cost_per_1000_pages(self) -> float:
        return 0.0

    def initialize(self) -> tuple[bool, str]:
        """Check if Tesseract is available and has required languages."""
        try:
            result = subprocess.run(
                ["tesseract", "--version"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
            )
            version_line = result.stdout.split("\n")[0]
        except (subprocess.SubprocessError, FileNotFoundError):
            return False, (
                "Tesseract not installed. Install with:\n"
                "  macOS: brew install tesseract tesseract-lang\n"
                "  Ubuntu: apt install tesseract-ocr tesseract-ocr-hin "
                "tesseract-ocr-san"
            )

        try:
            result = subprocess.run(
                ["tesseract", "--list-langs"],
                capture_output=True,
                text=True,
                timeout=_SUBPROCESS_TIMEOUT,
            )
            available_langs = result.stdout.lower()
        except subprocess.SubprocessError:
            available_langs = ""

        missing_langs = [
            lang for lang in self.languages if lang.lower() not in available_langs
        ]

        if missing_langs:
            return False, (
                f"Missing language data: {', '.join(missing_langs)}\n"
                "Install with:\n"
                "  macOS: brew install tesseract-lang\n"
                "  Ubuntu: apt install tesseract-ocr-hin tesseract-ocr-san"
            )

        try:
            import pytesseract

            self._tesseract = pytesseract
        except ImportError:
            return False, (
                "pytesseract not installed. Install with:\n"
                "  pip install pytesseract"
            )

        self._initialized = True
        return True, (
            f"Tesseract ready ({version_line}, "
            f"languages: {'+'.join(self.languages)})"
        )

    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process image with Tesseract.

        Args:
            image: PIL Image of the page.
            page_num: Page number for reference.

        Returns:
            OCRResult with extracted text and confidence score.
        """
        if not self._initialized or not self._tesseract:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Backend not initialized",
                backend_used=self.name,
            )

        start_time = time.time()

        try:
            if image.mode != "RGB":
                image = image.convert("RGB")

            lang_str = "+".join(self.languages)
            custom_config = f"--oem {self.oem} --psm {self.psm}"

            text = self._tesseract.image_to_string(
                image,
                lang=lang_str,
                config=custom_config,
            )

            avg_confidence = self._get_confidence(image, lang_str, custom_config)

            return OCRResult(
                page_num=page_num,
                text=text.strip(),
                success=True,
                confidence=avg_confidence,
                duration=time.time() - start_time,
                backend_used=self.name,
                needs_verification=self.contains_mantra(text),
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

    def _get_confidence(
        self, image: Image.Image, lang_str: str, custom_config: str
    ) -> float:
        """Extract average confidence from Tesseract.

        Args:
            image: PIL Image already in RGB mode.
            lang_str: Tesseract language string.
            custom_config: Tesseract config flags.

        Returns:
            Average confidence as a float between 0.0 and 1.0.
        """
        try:
            data = self._tesseract.image_to_data(
                image,
                lang=lang_str,
                config=custom_config,
                output_type=self._tesseract.Output.DICT,
            )
            confidences = [
                int(c)
                for c in data.get("conf", [])
                if str(c).lstrip("-").isdigit() and int(c) >= 0
            ]
            if confidences:
                return sum(confidences) / len(confidences) / 100
        except Exception:
            pass
        return 0.7
