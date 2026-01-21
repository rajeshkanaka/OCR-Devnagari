"""
Base class and types for OCR backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
from PIL import Image


class BackendType(Enum):
    """Available OCR backend types"""
    GEMINI = "gemini"
    MARKER = "marker"
    EASYOCR = "easyocr"
    TESSERACT = "tesseract"
    HYBRID = "hybrid"


@dataclass
class OCRResult:
    """Result of OCR processing for a single page"""
    page_num: int
    text: str
    success: bool
    confidence: float = 1.0  # 0.0 to 1.0, used for hybrid approach
    error: Optional[str] = None
    duration: float = 0.0
    backend_used: str = ""
    needs_verification: bool = False  # True if mantras detected
    
    @property
    def is_low_confidence(self) -> bool:
        """Check if result needs LLM verification"""
        return self.confidence < 0.85 or self.needs_verification


@dataclass
class BackendConfig:
    """Common configuration for all backends"""
    dpi: int = 200
    languages: list[str] = field(default_factory=lambda: ["hi", "sa", "en"])
    confidence_threshold: float = 0.85
    detect_mantras: bool = True


class OCRBackend(ABC):
    """Abstract base class for OCR backends"""
    
    def __init__(self, config: Optional[BackendConfig] = None):
        self.config = config or BackendConfig()
        self._initialized = False
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Return the backend name"""
        pass
    
    @property
    @abstractmethod
    def is_free(self) -> bool:
        """Return True if this backend is free (runs locally)"""
        pass
    
    @property
    def cost_per_1000_pages(self) -> float:
        """Estimated cost per 1000 pages in USD"""
        return 0.0 if self.is_free else 5.0  # Default for paid APIs
    
    @abstractmethod
    def initialize(self) -> tuple[bool, str]:
        """
        Initialize the backend (check dependencies, auth, etc.)
        
        Returns:
            Tuple of (success, message)
        """
        pass
    
    @abstractmethod
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """
        Process a single image and extract text.
        
        Args:
            image: PIL Image of the page
            page_num: Page number for reference
        
        Returns:
            OCRResult with extracted text and metadata
        """
        pass
    
    def process_pdf_page(self, pdf_path: Path, page_num: int, dpi: int = 200) -> OCRResult:
        """
        Process a single PDF page.
        
        Args:
            pdf_path: Path to PDF file
            page_num: Page number (1-indexed)
            dpi: Resolution for rendering
        
        Returns:
            OCRResult with extracted text
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
    
    def cleanup(self) -> None:
        """Cleanup any resources (override if needed)"""
        pass
