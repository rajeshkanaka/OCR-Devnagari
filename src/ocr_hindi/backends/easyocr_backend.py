"""
EasyOCR backend - Open-source OCR with excellent Hindi/Devanagari support.
FREE - Runs locally on CPU/GPU.

EasyOCR supports 80+ languages including Hindi (hi), Sanskrit transliteration.
"""

import time
from typing import Optional
from PIL import Image
from termcolor import colored

from .base import OCRBackend, OCRResult, BackendConfig


class EasyOCRBackend(OCRBackend):
    """
    EasyOCR backend for Hindi/Sanskrit OCR.
    
    Cost: $0 (runs locally)
    Accuracy: Good for printed Devanagari text
    
    Languages supported:
    - hi: Hindi
    - en: English (for mixed text)
    - sa: Sanskrit (via Devanagari support)
    """
    
    def __init__(
        self,
        config: Optional[BackendConfig] = None,
        use_gpu: bool = True,
        languages: Optional[list[str]] = None,
    ):
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
        """Initialize EasyOCR reader"""
        try:
            try:
                import easyocr
            except ImportError:
                return False, (
                    "EasyOCR not installed. Install with:\n"
                    "  pip install easyocr\n"
                    "  # For GPU support, ensure torch with CUDA is installed"
                )
            
            # Suppress EasyOCR/torch warnings
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
                return True, f"EasyOCR ready ({device_info}, languages: {', '.join(self.languages)})"
                
            except Exception as e:
                return False, f"Failed to load EasyOCR models: {str(e)}"
            
        except Exception as e:
            return False, f"EasyOCR initialization failed: {str(e)}"
    
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process image with EasyOCR"""
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
            
            # Convert PIL Image to numpy array
            image_array = np.array(image)
            
            # Run OCR with detail=1 to get confidence scores
            results = self._reader.readtext(
                image_array,
                detail=1,
                paragraph=True,  # Group text into paragraphs
            )
            
            if not results:
                duration = time.time() - start_time
                return OCRResult(
                    page_num=page_num,
                    text="",
                    success=True,
                    confidence=0.0,
                    duration=duration,
                    backend_used=self.name,
                )
            
            # Extract text and calculate average confidence
            texts = []
            confidences = []
            
            for item in results:
                if len(item) >= 2:
                    # item format: (bbox, text, confidence) or (bbox, text)
                    text = item[1]
                    confidence = item[2] if len(item) > 2 else 0.8
                    texts.append(text)
                    confidences.append(confidence)
            
            full_text = "\n".join(texts)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
            
            duration = time.time() - start_time
            
            # Check for mantras
            needs_verification = self._contains_mantra(full_text)
            
            return OCRResult(
                page_num=page_num,
                text=full_text,
                success=True,
                confidence=avg_confidence,
                duration=duration,
                backend_used=self.name,
                needs_verification=needs_verification,
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return OCRResult(
                page_num=page_num,
                text="",
                success=False,
                error=str(e),
                duration=duration,
                backend_used=self.name,
            )
    
    def _contains_mantra(self, text: str) -> bool:
        """Check if text contains mantra patterns"""
        mantra_patterns = [
            "॥", "ॐ", "स्वाहा", "नमः", "फट्", "हुं",
            "ह्रीं", "श्रीं", "क्लीं", "ऐं",
        ]
        
        if not self.config.detect_mantras:
            return False
        
        return any(pattern in text for pattern in mantra_patterns)
    
    def cleanup(self) -> None:
        """Free reader memory"""
        if self._reader is not None:
            del self._reader
            self._reader = None
