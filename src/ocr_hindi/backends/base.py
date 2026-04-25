"""Base class and types for OCR backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from PIL import Image

# Shared mantra patterns used across all backends for consistency
MANTRA_PATTERNS: tuple[str, ...] = (
    "\u0965",  # ॥ double danda
    "\u0950",  # ॐ Om
    "\u0938\u094d\u0935\u093e\u0939\u093e",  # स्वाहा
    "\u0928\u092e\u0903",  # नमः
    "\u092b\u091f\u094d",  # फट्
    "\u0939\u0941\u0902",  # हुं
    "\u0939\u094d\u0930\u0940\u0902",  # ह्रीं
    "\u0936\u094d\u0930\u0940\u0902",  # श्रीं
    "\u0915\u094d\u0932\u0940\u0902",  # क्लीं
    "\u0910\u0902",  # ऐं
)


class BackendType(Enum):
    """Available OCR backend types."""

    GEMINI = "gemini"
    MARKER = "marker"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    HYBRID = "hybrid"
    CHANDRA = "chandra"


@dataclass
class OCRResult:
    """Result of OCR processing for a single page."""

    page_num: int
    text: str
    success: bool
    confidence: float = 1.0
    error: str | None = None
    duration: float = 0.0
    backend_used: str = ""
    needs_verification: bool = False

    @property
    def is_low_confidence(self) -> bool:
        """Check if result needs LLM verification."""
        return self.confidence < 0.85 or self.needs_verification


@dataclass
class BackendConfig:
    """Common configuration for all backends."""

    dpi: int = 200
    languages: list[str] = field(default_factory=lambda: ["hi", "sa", "en"])
    confidence_threshold: float = 0.85
    detect_mantras: bool = True


class OCRBackend(ABC):
    """Abstract base class for OCR backends."""

    def __init__(self, config: BackendConfig | None = None) -> None:
        self.config = config or BackendConfig()
        self._initialized = False

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name."""

    @property
    @abstractmethod
    def is_free(self) -> bool:
        """Return True if this backend is free (runs locally)."""

    @property
    def cost_per_1000_pages(self) -> float:
        """Estimated cost per 1000 pages in USD."""
        return 0.0 if self.is_free else 5.0

    @abstractmethod
    def initialize(self) -> tuple[bool, str]:
        """Initialize the backend (check dependencies, auth, etc.).

        Returns:
            Tuple of (success, message).
        """

    @abstractmethod
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process a single image and extract text.

        Args:
            image: PIL Image of the page.
            page_num: Page number for reference.

        Returns:
            OCRResult with extracted text and metadata.
        """

    def process_pdf_page(self, pdf_path: Path, page_num: int, dpi: int = 200) -> OCRResult:
        """Process a single PDF page.

        Args:
            pdf_path: Path to PDF file.
            page_num: Page number (1-indexed).
            dpi: Resolution for rendering.

        Returns:
            OCRResult with extracted text.
        """
        from pdf2image import convert_from_path

        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num,
            last_page=page_num,
            fmt="png",
        )

        if not images:
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error="Failed to convert PDF page to image",
                backend_used=self.name,
            )

        return self.process_image(images[0], page_num)

    def contains_mantra(self, text: str) -> bool:
        """Check if text contains mantra patterns.

        Uses the shared MANTRA_PATTERNS constant for consistency
        across all backends.

        Args:
            text: Text to check for mantra patterns.

        Returns:
            True if mantras detected and detection is enabled.
        """
        if not self.config.detect_mantras:
            return False
        return any(pattern in text for pattern in MANTRA_PATTERNS)

    def cleanup(self) -> None:
        """Cleanup any resources (override if needed)."""
