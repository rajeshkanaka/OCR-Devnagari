"""
Tesseract OCR backend - Google's open-source OCR engine.
FREE - Runs locally.

Tesseract supports Hindi (hin) and Sanskrit (san) languages.
Requires tesseract-ocr to be installed on the system.
"""

import time
import subprocess
from typing import Optional
from PIL import Image
from termcolor import colored

from .base import OCRBackend, OCRResult, BackendConfig


class TesseractBackend(OCRBackend):
    """
    Tesseract OCR backend.
    
    Cost: $0 (runs locally)
    Accuracy: Good, may need training for old manuscripts
    
    System requirements:
    - macOS: brew install tesseract tesseract-lang
    - Ubuntu: apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san
    """
    
    def __init__(
        self,
        config: Optional[BackendConfig] = None,
        languages: Optional[list[str]] = None,
        oem: int = 3,  # OCR Engine Mode: 3 = default (LSTM + legacy)
        psm: int = 3,  # Page Segmentation Mode: 3 = auto
    ):
        super().__init__(config)
        # Tesseract uses 3-letter codes
        self.languages = languages or ["hin", "san", "eng"]
        self.oem = oem
        self.psm = psm
        self._tesseract_path = None
    
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
        """Check if Tesseract is available"""
        try:
            print(colored("  Initializing Tesseract backend...", "cyan"))
            
            # Check if tesseract is installed
            try:
                result = subprocess.run(
                    ["tesseract", "--version"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                version_line = result.stdout.split("\n")[0]
            except (subprocess.SubprocessError, FileNotFoundError):
                return False, (
                    "Tesseract not installed. Install with:\n"
                    "  macOS: brew install tesseract tesseract-lang\n"
                    "  Ubuntu: apt install tesseract-ocr tesseract-ocr-hin tesseract-ocr-san"
                )
            
            # Check for required language data
            try:
                result = subprocess.run(
                    ["tesseract", "--list-langs"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                available_langs = result.stdout.lower()
            except subprocess.SubprocessError:
                available_langs = ""
            
            missing_langs = []
            for lang in self.languages:
                if lang.lower() not in available_langs:
                    missing_langs.append(lang)
            
            if missing_langs:
                return False, (
                    f"Missing language data: {', '.join(missing_langs)}\n"
                    "Install with:\n"
                    "  macOS: brew install tesseract-lang\n"
                    "  Ubuntu: apt install tesseract-ocr-hin tesseract-ocr-san"
                )
            
            # Try importing pytesseract
            try:
                import pytesseract
                self._tesseract = pytesseract
            except ImportError:
                return False, (
                    "pytesseract not installed. Install with:\n"
                    "  pip install pytesseract"
                )
            
            self._initialized = True
            return True, f"Tesseract ready ({version_line}, languages: {'+'.join(self.languages)})"
            
        except Exception as e:
            return False, f"Tesseract initialization failed: {str(e)}"
    
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """Process image with Tesseract"""
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
            # Convert to RGB if needed
            if image.mode != "RGB":
                image = image.convert("RGB")
            
            # Build language string (e.g., "hin+san+eng")
            lang_str = "+".join(self.languages)
            
            # Configure tesseract
            custom_config = f"--oem {self.oem} --psm {self.psm}"
            
            # Get text and confidence data
            text = self._tesseract.image_to_string(
                image,
                lang=lang_str,
                config=custom_config,
            )
            
            # Get confidence data
            try:
                data = self._tesseract.image_to_data(
                    image,
                    lang=lang_str,
                    config=custom_config,
                    output_type=self._tesseract.Output.DICT,
                )
                
                # Calculate average confidence (filter out -1 values)
                confidences = [
                    int(c) for c in data.get("conf", [])
                    if str(c).lstrip("-").isdigit() and int(c) >= 0
                ]
                avg_confidence = sum(confidences) / len(confidences) / 100 if confidences else 0.5
                
            except Exception:
                avg_confidence = 0.7  # Default if confidence extraction fails
            
            duration = time.time() - start_time
            
            # Check for mantras
            needs_verification = self._contains_mantra(text)
            
            return OCRResult(
                page_num=page_num,
                text=text.strip(),
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
