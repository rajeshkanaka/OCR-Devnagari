"""
Marker backend - Open-source PDF to Markdown conversion.
FREE - Runs locally on CPU/GPU/MPS.

Marker is highly accurate for books and manuscripts.
Best option for bulk processing with excellent Markdown output.
"""

import time
from pathlib import Path
from typing import Optional
from PIL import Image
from termcolor import colored

from .base import OCRBackend, OCRResult, BackendConfig


class MarkerBackend(OCRBackend):
    """
    Marker PDF to Markdown backend.
    
    Cost: $0 (runs locally)
    Accuracy: Very good for structured documents
    
    Note: Marker works on entire PDFs, not individual images.
    For page-by-page processing, it converts then extracts.
    """
    
    def __init__(
        self,
        config: Optional[BackendConfig] = None,
        use_gpu: bool = True,
        batch_size: int = 10,
    ):
        super().__init__(config)
        self.use_gpu = use_gpu
        self.batch_size = batch_size
        self._marker_available = False
        self._model = None
    
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
        """Check if Marker is available and load models"""
        try:
            print(colored("  Initializing Marker backend...", "cyan"))
            
            # Try to import marker
            try:
                from marker.converters.pdf import PdfConverter
                from marker.models import create_model_dict
                from marker.output import text_from_rendered
            except ImportError:
                return False, (
                    "Marker not installed. Install with:\n"
                    "  pip install marker-pdf\n"
                    "  # For GPU support:\n"
                    "  pip install marker-pdf[gpu]"
                )
            
            # Try to load models (this may take a moment on first run)
            print(colored("  Loading Marker models (may take a moment)...", "yellow"))
            
            try:
                self._model_dict = create_model_dict()
                self._converter = PdfConverter(artifact_dict=self._model_dict)
                self._marker_available = True
                self._initialized = True
                
                device_info = "GPU" if self.use_gpu else "CPU"
                return True, f"Marker ready ({device_info})"
                
            except Exception as e:
                return False, f"Failed to load Marker models: {str(e)}"
            
        except Exception as e:
            return False, f"Marker initialization failed: {str(e)}"
    
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """
        Process a single image with Marker.
        
        Note: Marker is optimized for PDF processing, not individual images.
        For single images, we save to temp PDF and process.
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
            
            # Save image as temp PDF
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                # Convert to RGB if needed
                if image.mode != "RGB":
                    image = image.convert("RGB")
                image.save(tmp.name, "PDF")
                tmp_path = Path(tmp.name)
            
            try:
                # Process with Marker
                rendered = self._converter(str(tmp_path))
                text = text_from_rendered(rendered)
                
                duration = time.time() - start_time
                
                # Estimate confidence based on text quality
                confidence = self._estimate_confidence(text)
                needs_verification = self._contains_mantra(text)
                
                return OCRResult(
                    page_num=page_num,
                    text=text.strip(),
                    success=True,
                    confidence=confidence,
                    duration=duration,
                    backend_used=self.name,
                    needs_verification=needs_verification,
                )
                
            finally:
                # Cleanup temp file
                tmp_path.unlink(missing_ok=True)
                
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
    
    def process_pdf(self, pdf_path: Path) -> tuple[dict[int, str], float]:
        """
        Process entire PDF at once (more efficient for Marker).
        
        Args:
            pdf_path: Path to PDF file
        
        Returns:
            Tuple of (dict mapping page_num to text, total_duration)
        """
        if not self._initialized:
            raise RuntimeError("Backend not initialized")
        
        start_time = time.time()
        
        from marker.output import text_from_rendered
        
        # Process entire PDF
        rendered = self._converter(str(pdf_path))
        
        # Get text per page if available, otherwise split by page markers
        full_text = text_from_rendered(rendered)
        
        # Try to split by page markers
        pages = self._split_by_pages(full_text)
        
        duration = time.time() - start_time
        
        return pages, duration
    
    def _split_by_pages(self, text: str) -> dict[int, str]:
        """Split combined text by page markers"""
        import re
        
        # Look for page markers (Marker may add these)
        pages = {}
        
        # Try common page marker patterns
        page_pattern = r'(?:^|\n)(?:---\s*)?(?:Page|PAGE|page)\s*(\d+)(?:\s*---)?(?:\n|$)'
        matches = list(re.finditer(page_pattern, text))
        
        if matches:
            for i, match in enumerate(matches):
                page_num = int(match.group(1))
                start = match.end()
                end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
                pages[page_num] = text[start:end].strip()
        else:
            # No page markers, treat as single page
            pages[1] = text.strip()
        
        return pages
    
    def _estimate_confidence(self, text: str) -> float:
        """Estimate OCR confidence based on text quality"""
        if not text:
            return 0.0
        
        # Check for common OCR issues
        issues = 0
        
        # Too many consecutive special characters (garbled text)
        import re
        if re.search(r'[^\w\s]{5,}', text):
            issues += 1
        
        # Very short text for a page (likely failed)
        if len(text) < 50:
            issues += 1
        
        # High ratio of numbers/symbols to letters
        letters = sum(1 for c in text if c.isalpha())
        if letters < len(text) * 0.3:
            issues += 1
        
        # Calculate confidence
        confidence = max(0.5, 1.0 - (issues * 0.15))
        
        return confidence
    
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
        """Free model memory"""
        if hasattr(self, '_model_dict'):
            del self._model_dict
        if hasattr(self, '_converter'):
            del self._converter
