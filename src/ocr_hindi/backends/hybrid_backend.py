"""
Hybrid OCR backend - Combines free OCR with LLM verification.
90%+ cost savings compared to pure Gemini approach.

Strategy:
1. Use EasyOCR (free) for initial extraction
2. Calculate confidence score for each page
3. Only use Gemini for:
   - Low confidence pages (<85%)
   - Pages containing mantras (critical accuracy)

Model: gemini-3-flash-preview
Pricing (per 1M tokens): $0.50 input / $3.00 output
Cost: ~$0.50-1 per 1000 pages (vs $2+ for pure Gemini)
"""

import time
from typing import Optional
from PIL import Image
from termcolor import colored

from .base import OCRBackend, OCRResult, BackendConfig
from .easyocr_backend import EasyOCRBackend
from .gemini_backend import GeminiBackend, TokenUsage
from .mantra_detector import MantraDetector


class HybridBackend(OCRBackend):
    """
    Hybrid OCR backend for maximum cost savings with maintained accuracy.
    
    Uses gemini-3-flash-preview with optimized settings:
    - thinking_level: "low" for fast OCR
    - Token tracking for accurate cost calculation
    
    Configuration:
    - confidence_threshold: Pages below this get Gemini verification (default: 0.85)
    - verify_mantras: Always verify pages with mantras (default: True)
    - primary_backend: Which free backend to use (default: easyocr)
    """
    
    def __init__(
        self,
        config: Optional[BackendConfig] = None,
        confidence_threshold: float = 0.85,
        verify_mantras: bool = True,
        primary_backend: str = "easyocr",
        gemini_model: str = "gemini-3-flash-preview",
        thinking_level: str = "low",  # Optimal for OCR tasks
    ):
        super().__init__(config)
        self.confidence_threshold = confidence_threshold
        self.verify_mantras = verify_mantras
        self.primary_backend_type = primary_backend
        self.gemini_model = gemini_model
        self.thinking_level = thinking_level
        
        self._primary: Optional[OCRBackend] = None
        self._gemini: Optional[GeminiBackend] = None
        self._mantra_detector = MantraDetector(strict_mode=verify_mantras)
        
        # Token usage tracking (aggregated from Gemini calls)
        self.token_usage = TokenUsage()
        
        # Quiet mode (less verbose output)
        self._quiet = False
        
        # Stats tracking
        self._stats = {
            "total_pages": 0,
            "primary_only": 0,
            "gemini_verified": 0,
            "gemini_for_low_confidence": 0,
            "gemini_for_mantras": 0,
            "total_duration": 0.0,
        }
    
    def set_quiet(self, quiet: bool) -> None:
        """Enable/disable quiet mode"""
        self._quiet = quiet
    
    @property
    def name(self) -> str:
        return "hybrid"
    
    @property
    def is_free(self) -> bool:
        return False  # Uses Gemini for some pages
    
    @property
    def cost_per_1000_pages(self) -> float:
        # Estimate: ~10-20% of pages need Gemini
        gemini_ratio = 0.15
        return GeminiBackend().cost_per_1000_pages * gemini_ratio
    
    def initialize(self) -> tuple[bool, str]:
        """Initialize both primary (free) and Gemini backends"""
        try:
            # Initialize primary backend silently
            if self.primary_backend_type == "easyocr":
                self._primary = EasyOCRBackend(config=self.config)
            elif self.primary_backend_type == "tesseract":
                from .tesseract_backend import TesseractBackend
                self._primary = TesseractBackend(config=self.config)
            else:
                return False, f"Unknown primary backend: {self.primary_backend_type}"
            
            # Suppress backend initialization output
            import sys
            import io
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()
            
            try:
                success, msg = self._primary.initialize()
            finally:
                sys.stdout = old_stdout
                
            if not success:
                return False, f"Primary backend failed: {msg}"
            
            # Initialize Gemini backend for verification (silently)
            self._gemini = GeminiBackend(
                config=self.config,
                model=self.gemini_model,
                thinking_level=self.thinking_level,
            )
            
            sys.stdout = io.StringIO()
            try:
                success, msg = self._gemini.initialize()
            finally:
                sys.stdout = old_stdout
                
            if not success:
                return False, f"Gemini backend failed: {msg}"
            
            self._initialized = True
            return True, f"Ready"
            
        except Exception as e:
            return False, f"Hybrid initialization failed: {str(e)}"
    
    def process_image(self, image: Image.Image, page_num: int) -> OCRResult:
        """
        Process image with hybrid approach:
        1. Try primary (free) backend
        2. If low confidence or contains mantras, verify with Gemini
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
        self._stats["total_pages"] += 1
        
        # Step 1: Process with primary backend
        primary_result = self._primary.process_image(image, page_num)
        
        if not primary_result.success:
            # Primary failed, try Gemini directly
            gemini_result = self._gemini.process_image(image, page_num)
            gemini_result.backend_used = f"{self.name}:gemini-fallback"
            self._stats["gemini_verified"] += 1
            self._stats["total_duration"] += time.time() - start_time
            
            # Update token usage
            self._sync_token_usage()
            
            return gemini_result
        
        # Step 2: Decide if Gemini verification is needed
        needs_gemini = False
        reason = ""
        
        if primary_result.confidence < self.confidence_threshold:
            needs_gemini = True
            reason = f"low confidence ({primary_result.confidence:.0%})"
            self._stats["gemini_for_low_confidence"] += 1
        
        if self.verify_mantras:
            mantra_result = self._mantra_detector.detect(primary_result.text)
            if mantra_result.recommendation in ("verify", "high_priority"):
                needs_gemini = True
                reason = f"mantra verification ({mantra_result.recommendation})"
                self._stats["gemini_for_mantras"] += 1
        
        # Step 3: Use Gemini if needed
        if needs_gemini:
            gemini_result = self._gemini.process_image(image, page_num)
            
            # Update token usage
            self._sync_token_usage()
            
            if gemini_result.success:
                # Use Gemini result (more accurate for this case)
                gemini_result.duration = time.time() - start_time
                gemini_result.backend_used = f"{self.name}:{self.primary_backend_type}+gemini"
                self._stats["gemini_verified"] += 1
                self._stats["total_duration"] += gemini_result.duration
                return gemini_result
            else:
                # Gemini failed, fall back to primary result
                primary_result.backend_used = f"{self.name}:{self.primary_backend_type}-fallback"
                self._stats["total_duration"] += time.time() - start_time
                return primary_result
        
        # Step 4: Use primary result (high confidence, no mantras)
        self._stats["primary_only"] += 1
        primary_result.duration = time.time() - start_time
        primary_result.backend_used = f"{self.name}:{self.primary_backend_type}"
        self._stats["total_duration"] += primary_result.duration
        return primary_result
    
    def _sync_token_usage(self) -> None:
        """Sync token usage from Gemini backend"""
        if self._gemini:
            self.token_usage = self._gemini.token_usage
    
    def get_token_usage(self) -> TokenUsage:
        """Get current token usage"""
        self._sync_token_usage()
        return self.token_usage
    
    def get_cost(self) -> float:
        """Get total Gemini API cost in USD"""
        self._sync_token_usage()
        return self.token_usage.total_cost
    
    def get_stats(self) -> dict:
        """Get processing statistics"""
        stats = self._stats.copy()
        
        if stats["total_pages"] > 0:
            stats["primary_only_pct"] = stats["primary_only"] / stats["total_pages"] * 100
            stats["gemini_verified_pct"] = stats["gemini_verified"] / stats["total_pages"] * 100
            stats["estimated_savings_pct"] = stats["primary_only_pct"]
        
        # Add cost info
        self._sync_token_usage()
        stats["token_usage"] = self.token_usage
        stats["total_cost"] = self.token_usage.total_cost
        
        return stats
    
    def print_stats(self) -> None:
        """Print processing statistics with cost breakdown using Rich"""
        from rich.console import Console
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text
        from rich import box
        
        console = Console()
        stats = self.get_stats()
        usage = stats.get("token_usage", self.token_usage)
        
        console.print()
        
        # Create main stats table
        stats_table = Table(box=box.ROUNDED, show_header=False, border_style="cyan")
        stats_table.add_column("Metric", style="dim", width=24)
        stats_table.add_column("Value", style="bold", width=20)
        stats_table.add_column("Detail", style="dim", width=20)
        
        # Model info
        stats_table.add_row("🤖 Model", self.gemini_model, f"thinking: {self.thinking_level}")
        stats_table.add_row("", "", "")  # Spacer
        
        # Page stats
        primary_pct = stats.get('primary_only_pct', 0)
        gemini_pct = stats.get('gemini_verified_pct', 0)
        stats_table.add_row("📄 Pages Processed", str(stats['total_pages']), "")
        stats_table.add_row("   └─ FREE (local)", f"{stats['primary_only']}", f"[green]{primary_pct:.0f}%[/green]")
        stats_table.add_row("   └─ Gemini API", f"{stats['gemini_verified']}", f"[yellow]{gemini_pct:.0f}%[/yellow]")
        stats_table.add_row("", "", "")  # Spacer
        
        # Token stats
        stats_table.add_row("🔢 Tokens Used", f"{usage.total_tokens:,}", "")
        stats_table.add_row("   └─ Input", f"{usage.input_tokens:,}", "$0.50/1M")
        stats_table.add_row("   └─ Output", f"{usage.output_tokens:,}", "$3.00/1M")
        
        console.print(Panel(
            stats_table,
            title="[bold cyan]📊 Processing Summary[/bold cyan]",
            border_style="cyan"
        ))
        
        # Cost panel
        if stats["total_pages"] > 0:
            # Calculate FREE vs API pages
            free_pages = stats.get("primary_only", 0)
            api_pages = stats.get("gemini_verified", 0)
            
            cost_text = Text()
            cost_text.append(f"Total: ", style="dim")
            cost_text.append(f"${usage.total_cost:.4f}", style="bold green")
            cost_text.append(f"  │  ", style="dim")
            cost_text.append(f"FREE pages: ", style="dim")
            cost_text.append(f"{free_pages}", style="bold yellow")
            cost_text.append(f"  │  ", style="dim")
            cost_text.append(f"API pages: ", style="dim")
            cost_text.append(f"{api_pages}", style="bold cyan")
            
            if free_pages > 0:
                # Show savings only if we actually saved
                savings_pct = (free_pages / stats["total_pages"]) * 100
                cost_text.append(f"  │  ", style="dim")
                cost_text.append(f"Savings: ", style="dim")
                cost_text.append(f"{savings_pct:.0f}%", style="bold green")
            
            console.print(Panel(
                cost_text,
                title="[bold green]💰 Cost[/bold green]",
                border_style="green"
            ))
        
        console.print()
    
    def cleanup(self) -> None:
        """Cleanup both backends"""
        if self._primary:
            self._primary.cleanup()
        if self._gemini:
            self._gemini.cleanup()
