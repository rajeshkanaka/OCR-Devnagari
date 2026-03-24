"""OCR Backend implementations for cost-effective processing.

Available backends:

- gemini: Original Gemini Vision API (expensive but accurate)
- marker: Open-source PDF to Markdown (FREE, runs locally)
- easyocr: Open-source OCR with Hindi support (FREE, runs locally)
- tesseract: Google's open-source OCR (FREE, runs locally)
- hybrid: EasyOCR + Gemini for low-confidence pages (90%+ cost savings)
"""

from .base import BackendConfig, BackendType, OCRBackend, OCRResult
from .easyocr_backend import EasyOCRBackend
from .gemini_backend import GeminiBackend, TokenUsage
from .hybrid_backend import HybridBackend
from .mantra_detector import MantraDetector, detect_mantras
from .marker_backend import MarkerBackend
from .tesseract_backend import TesseractBackend

__all__ = [
    "BackendConfig",
    "BackendType",
    "EasyOCRBackend",
    "GeminiBackend",
    "HybridBackend",
    "MantraDetector",
    "MarkerBackend",
    "OCRBackend",
    "OCRResult",
    "TesseractBackend",
    "TokenUsage",
    "detect_mantras",
    "get_backend",
]

_BACKEND_MAP: dict[str, type[OCRBackend]] = {
    "gemini": GeminiBackend,
    "marker": MarkerBackend,
    "easyocr": EasyOCRBackend,
    "tesseract": TesseractBackend,
    "hybrid": HybridBackend,
}


def get_backend(backend_type: str, **kwargs) -> OCRBackend:
    """Factory function to get the appropriate OCR backend.

    Args:
        backend_type: One of 'gemini', 'marker', 'easyocr', 'tesseract', 'hybrid'.
        **kwargs: Backend-specific configuration options.

    Returns:
        Configured OCR backend instance.

    Raises:
        ValueError: If backend_type is not recognized.
    """
    backend_type = backend_type.lower()
    cls = _BACKEND_MAP.get(backend_type)

    if cls is None:
        available = ", ".join(sorted(_BACKEND_MAP))
        raise ValueError(
            f"Unknown backend: {backend_type}. Available: {available}"
        )

    return cls(**kwargs)
