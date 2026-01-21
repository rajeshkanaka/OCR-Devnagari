"""
OCR Backend implementations for cost-effective processing.

Available backends:
- gemini: Original Gemini Vision API (expensive but accurate)
- marker: Open-source PDF to Markdown (FREE, runs locally)
- easyocr: Open-source OCR with Hindi support (FREE, runs locally)
- tesseract: Google's open-source OCR (FREE, runs locally)
- hybrid: EasyOCR + Gemini for low-confidence pages (90%+ cost savings)
"""

from .base import OCRBackend, OCRResult, BackendType, BackendConfig
from .gemini_backend import GeminiBackend, TokenUsage
from .marker_backend import MarkerBackend
from .easyocr_backend import EasyOCRBackend
from .tesseract_backend import TesseractBackend
from .hybrid_backend import HybridBackend
from .mantra_detector import MantraDetector, detect_mantras

__all__ = [
    "OCRBackend",
    "OCRResult",
    "BackendType",
    "BackendConfig",
    "TokenUsage",
    "GeminiBackend",
    "MarkerBackend",
    "EasyOCRBackend",
    "TesseractBackend",
    "HybridBackend",
    "MantraDetector",
    "detect_mantras",
]


def get_backend(backend_type: str, **kwargs) -> OCRBackend:
    """
    Factory function to get the appropriate OCR backend.
    
    Args:
        backend_type: One of 'gemini', 'marker', 'easyocr', 'tesseract', 'hybrid'
        **kwargs: Backend-specific configuration options
    
    Returns:
        Configured OCR backend instance
    """
    backend_type = backend_type.lower()
    
    if backend_type == "gemini":
        return GeminiBackend(**kwargs)
    elif backend_type == "marker":
        return MarkerBackend(**kwargs)
    elif backend_type == "easyocr":
        return EasyOCRBackend(**kwargs)
    elif backend_type == "tesseract":
        return TesseractBackend(**kwargs)
    elif backend_type == "hybrid":
        return HybridBackend(**kwargs)
    else:
        raise ValueError(
            f"Unknown backend: {backend_type}. "
            f"Available: gemini, marker, easyocr, tesseract, hybrid"
        )
