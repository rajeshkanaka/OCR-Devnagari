"""OCR Hindi - Production-ready OCR for Hindi/Sanskrit PDFs using Gemini + Vertex AI."""

__version__ = "0.1.0"

__all__ = [
    "__version__",
    "OCRConfig",
    "OCRProcessor",
    "ProcessingResult",
]


def __getattr__(name: str):
    """Lazy imports to avoid side effects on module load."""
    if name == "OCRProcessor":
        from .processor import OCRProcessor
        return OCRProcessor
    if name == "OCRConfig":
        from .processor import OCRConfig
        return OCRConfig
    if name == "ProcessingResult":
        from .processor import ProcessingResult
        return ProcessingResult
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
