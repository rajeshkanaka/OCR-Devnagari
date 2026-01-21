"""
Multi-backend OCR processor supporting various engines.
Allows switching between Gemini, Marker, EasyOCR, Tesseract, and Hybrid modes.

Features:
- File-based cache for crash recovery (no data loss on crash)
- Graceful shutdown on Ctrl+C (saves all completed work)
- Memory-efficient processing (cleanup after each page)
- Resume capability (skip already cached pages)
"""

import asyncio
import gc
import logging
import signal
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pdf2image import convert_from_path
from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from termcolor import colored

from .backends import get_backend, OCRBackend, OCRResult
from .backends.base import BackendConfig
from .cache import OCRCache
from .utils import (
    ProgressState,
    format_duration,
    get_log_file,
    get_output_file,
    get_progress_file,
)

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class MultiProcessorConfig:
    """Configuration for multi-backend processor"""

    backend: str = "hybrid"  # gemini, marker, easyocr, tesseract, hybrid
    dpi: int = 200
    max_concurrent: int = 10
    confidence_threshold: float = 0.85
    detect_mantras: bool = True
    gemini_model: str = "gemini-3-flash-preview"


class MultiBackendProcessor:
    """
    OCR processor supporting multiple backends.

    Usage:
        processor = MultiBackendProcessor(config)
        processor.initialize()
        success, failed, output = processor.process_pdf(pdf_path, pages)
    """

    def __init__(self, config: Optional[MultiProcessorConfig] = None):
        self.config = config or MultiProcessorConfig()
        self._backend: Optional[OCRBackend] = None
        self._initialized = False

    def initialize(self, quiet: bool = False) -> tuple[bool, str, str]:
        """
        Initialize the selected backend.

        Args:
            quiet: If True, suppress verbose initialization output

        Returns:
            Tuple of (success, backend_name, message)
        """
        if not quiet:
            print(colored(f"\n  Initializing {self.config.backend} backend...", "cyan"))

        try:
            backend_config = BackendConfig(
                dpi=self.config.dpi,
                confidence_threshold=self.config.confidence_threshold,
                detect_mantras=self.config.detect_mantras,
            )

            # Get the appropriate backend
            backend_kwargs = {"config": backend_config}

            if self.config.backend == "gemini":
                backend_kwargs["model"] = self.config.gemini_model
            elif self.config.backend == "hybrid":
                backend_kwargs[
                    "confidence_threshold"
                ] = self.config.confidence_threshold
                backend_kwargs["verify_mantras"] = self.config.detect_mantras
                backend_kwargs["gemini_model"] = self.config.gemini_model

            self._backend = get_backend(self.config.backend, **backend_kwargs)

            # Set quiet mode for backends that support it
            if hasattr(self._backend, "set_quiet"):
                self._backend.set_quiet(quiet)

            success, message = self._backend.initialize()

            if success:
                self._initialized = True

            return success, self._backend.name, message

        except Exception as e:
            return False, "error", str(e)

    def process_pdf(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
    ) -> tuple[int, int, Path]:
        """
        Process PDF with the configured backend.

        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers to process (1-indexed)
            resume: Whether to resume from previous progress
            dry_run: Only show what would be processed

        Returns:
            Tuple of (successful_count, failed_count, output_path)
        """
        if not self._initialized:
            raise RuntimeError("Processor not initialized. Call initialize() first.")

        progress_file = get_progress_file(pdf_path)
        output_file = get_output_file(pdf_path)
        log_file = get_log_file(pdf_path)

        # Setup logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        # Load or create progress state
        state = None
        if resume:
            state = ProgressState.load(progress_file)
            if state:
                console.print(
                    f"[yellow]Resuming: {len(state.completed_pages)} pages done[/yellow]"
                )

        if not state:
            state = ProgressState(pdf_path=str(pdf_path), total_pages=max(pages))

        pending_pages = state.get_pending_pages(pages)

        if dry_run:
            self._print_dry_run(pdf_path, pages, state, pending_pages)
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All pages already processed![/green]")
            return len(state.completed_pages), len(state.failed_pages), output_file

        console.print(
            f"\n[bold]Processing {len(pending_pages)} pages with {self._backend.name}...[/bold]"
        )
        console.print(f"  Log: {log_file}")

        results: dict[int, str] = {}
        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("OCR Processing", total=len(pending_pages))

            for page_num in pending_pages:
                try:
                    progress.update(task, description=f"Page {page_num}")

                    # Convert page to image
                    images = convert_from_path(
                        pdf_path,
                        dpi=self.config.dpi,
                        first_page=page_num,
                        last_page=page_num,
                        fmt="png",
                    )

                    if not images:
                        logger.error(f"Page {page_num}: Failed to convert to image")
                        state.mark_failed(page_num)
                        progress.advance(task)
                        continue

                    # Process with backend
                    result = self._backend.process_image(images[0], page_num)

                    if result.success:
                        results[page_num] = result.text
                        state.mark_completed(page_num)
                        logger.info(
                            f"Page {page_num}: {len(result.text)} chars, "
                            f"confidence: {result.confidence:.0%}, "
                            f"backend: {result.backend_used}"
                        )
                    else:
                        state.mark_failed(page_num)
                        logger.error(f"Page {page_num}: {result.error}")

                    # Save progress
                    state.save(progress_file)
                    progress.advance(task)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted! Saving progress...[/yellow]")
                    state.save(progress_file)
                    raise

                except Exception as e:
                    logger.error(f"Page {page_num}: Unexpected error - {str(e)}")
                    state.mark_failed(page_num)
                    state.save(progress_file)
                    progress.advance(task)

        # Write output
        self._write_output(pdf_path, results, output_file, pages)

        total_time = time.time() - start_time
        logger.info(
            f"Complete: {len(state.completed_pages)} success, "
            f"{len(state.failed_pages)} failed, {format_duration(total_time)}"
        )

        # Print stats and cost summary
        if hasattr(self._backend, "print_stats"):
            self._backend.print_stats()
        elif hasattr(self._backend, "print_cost_summary"):
            self._backend.print_cost_summary()

        return len(state.completed_pages), len(state.failed_pages), output_file

    async def process_pdf_async(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
    ) -> tuple[int, int, Path]:
        """
        Async version of process_pdf with crash recovery and graceful shutdown.

        Features:
        - File-based cache: Each page saved to disk immediately (crash-safe)
        - Graceful shutdown: Ctrl+C saves all completed work
        - Memory efficient: Images cleaned up after each page
        - Resume capable: Skips already cached pages
        """
        if not self._initialized:
            raise RuntimeError("Processor not initialized. Call initialize() first.")

        progress_file = get_progress_file(pdf_path)
        output_file = get_output_file(pdf_path)
        log_file = get_log_file(pdf_path)

        # Setup logging
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        # Initialize file-based cache for crash recovery
        cache = OCRCache(pdf_path)

        # Graceful shutdown flag
        shutdown_requested = asyncio.Event()

        def handle_shutdown(signum, frame):
            """Handle shutdown signals gracefully."""
            console.print("\n[yellow]🛑 Shutdown requested, saving work...[/yellow]")
            shutdown_requested.set()

        # Setup signal handlers (only in main thread)
        original_sigint = signal.signal(signal.SIGINT, handle_shutdown)
        original_sigterm = signal.signal(signal.SIGTERM, handle_shutdown)

        # Load or create progress state
        state = None
        if resume:
            state = ProgressState.load(progress_file)
            if state:
                console.print(
                    f"[yellow]Resuming: {len(state.completed_pages)} pages done[/yellow]"
                )

        if not state:
            state = ProgressState(pdf_path=str(pdf_path), total_pages=max(pages))

        # Check cache for already processed pages (in addition to progress state)
        cached_pages = set(cache.pages())
        if resume and cached_pages:
            # Sync cache with state (in case state file was lost but cache exists)
            for page in cached_pages:
                if page not in state.completed_pages:
                    state.mark_completed(page)
            console.print(f"[yellow]Found {len(cached_pages)} pages in cache[/yellow]")

        pending_pages = state.get_pending_pages(pages)

        # Also exclude pages in cache (for crash recovery)
        pending_pages = [p for p in pending_pages if p not in cached_pages]

        if dry_run:
            self._print_dry_run(pdf_path, pages, state, pending_pages)
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All pages already processed![/green]")
            # Finalize from cache if needed
            self._finalize(cache, state, output_file, pdf_path)
            return len(state.completed_pages), len(state.failed_pages), output_file

        results: dict[int, str] = {}
        start_time = time.time()

        # Create temp directory for images
        temp_dir = Path(tempfile.mkdtemp(prefix="ocr_multi_"))
        image_paths: dict[int, Path] = {}

        try:
            # First, convert all pages to images
            image_paths = await self._convert_pages_async(
                pdf_path, pending_pages, temp_dir
            )

            # Create semaphore for concurrent processing
            semaphore = asyncio.Semaphore(self.config.max_concurrent)

            async def process_page(page_num: int) -> OCRResult:
                """Process a single page with memory cleanup."""
                async with semaphore:
                    if shutdown_requested.is_set():
                        return OCRResult(
                            page_num=page_num,
                            text="",
                            success=False,
                            error="Shutdown requested",
                            backend_used=self._backend.name,
                        )

                    if page_num not in image_paths:
                        return OCRResult(
                            page_num=page_num,
                            text="",
                            success=False,
                            error="Image not found",
                            backend_used=self._backend.name,
                        )

                    from PIL import Image

                    image = None
                    try:
                        image = Image.open(image_paths[page_num])

                        # Run in executor for CPU-bound work
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(
                            None, lambda: self._backend.process_image(image, page_num)
                        )
                        return result

                    finally:
                        # CRITICAL: Release memory immediately
                        if image:
                            image.close()
                            del image

                        # Delete temp image file to free disk space
                        try:
                            if page_num in image_paths:
                                image_paths[page_num].unlink(missing_ok=True)
                        except Exception:
                            pass

                        # Periodic garbage collection
                        if page_num % 10 == 0:
                            gc.collect()

            # Process all pages
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task("OCR Processing", total=len(pending_pages))

                tasks = [process_page(page_num) for page_num in pending_pages]

                for coro in asyncio.as_completed(tasks):
                    if shutdown_requested.is_set():
                        console.print("[yellow]Completing current tasks...[/yellow]")
                        break

                    result = await coro

                    if result.success:
                        # Save to cache IMMEDIATELY (crash-safe)
                        cache.save(
                            result.page_num,
                            result.text,
                            backend=result.backend_used,
                            confidence=result.confidence,
                        )
                        results[result.page_num] = result.text
                        state.mark_completed(result.page_num)
                        logger.info(
                            f"Page {result.page_num}: {len(result.text)} chars "
                            f"[cached to disk]"
                        )
                    else:
                        if result.error != "Shutdown requested":
                            state.mark_failed(result.page_num)
                            logger.error(f"Page {result.page_num}: {result.error}")

                    state.save(progress_file)
                    progress.advance(task)

        finally:
            # Restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

            # Cleanup remaining temp images
            for path in image_paths.values():
                try:
                    path.unlink(missing_ok=True)
                except Exception:
                    pass
            try:
                temp_dir.rmdir()
            except Exception:
                pass

            # Force garbage collection
            gc.collect()

        # ALWAYS finalize - merge cache to output file
        self._finalize(cache, state, output_file, pdf_path)

        total_time = time.time() - start_time
        logger.info(
            f"Complete: {len(state.completed_pages)} success, "
            f"{len(state.failed_pages)} failed, {format_duration(total_time)}"
        )

        # Print stats and cost summary
        if hasattr(self._backend, "print_stats"):
            self._backend.print_stats()
        elif hasattr(self._backend, "print_cost_summary"):
            self._backend.print_cost_summary()

        if shutdown_requested.is_set():
            console.print(
                f"[green]✓ Saved {len(state.completed_pages)} pages before shutdown[/green]"
            )
            console.print(f"[dim]  Resume with: --resume flag[/dim]")

        return len(state.completed_pages), len(state.failed_pages), output_file

    def _finalize(
        self,
        cache: OCRCache,
        state: ProgressState,
        output_file: Path,
        pdf_path: Path,
    ) -> None:
        """
        Finalize processing: merge cache to output file.

        This is called:
        - After normal completion
        - After graceful shutdown (Ctrl+C)
        - When resuming with all pages cached
        """
        # Load all results from cache
        cached_results = cache.all_results()

        if not cached_results:
            logger.warning("No cached results to finalize")
            return

        # Write to output file
        self._write_output(
            pdf_path, cached_results, output_file, list(cached_results.keys())
        )

        logger.info(f"Finalized {len(cached_results)} pages to {output_file}")
        console.print(
            f"[green]✓ Saved {len(cached_results)} pages to {output_file}[/green]"
        )

    async def _convert_pages_async(
        self,
        pdf_path: Path,
        pages: list[int],
        temp_dir: Path,
    ) -> dict[int, Path]:
        """Convert PDF pages to images asynchronously."""
        image_paths: dict[int, Path] = {}

        loop = asyncio.get_event_loop()

        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            for page_num in pages:
                future = loop.run_in_executor(
                    executor,
                    _convert_page,
                    str(pdf_path),
                    page_num,
                    self.config.dpi,
                    str(temp_dir),
                )
                futures.append((page_num, future))

            for page_num, future in futures:
                try:
                    path = await future
                    if path:
                        image_paths[page_num] = Path(path)
                except Exception as e:
                    logger.error(f"Failed to convert page {page_num}: {e}")

        return image_paths

    def _print_dry_run(
        self,
        pdf_path: Path,
        pages: list[int],
        state: ProgressState,
        pending: list[int],
    ) -> None:
        """Print dry run information."""
        from rich.table import Table

        table = Table(title="Dry Run - Processing Plan")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("PDF", str(pdf_path))
        table.add_row("Backend", self._backend.name)
        table.add_row(
            "Cost",
            "FREE"
            if self._backend.is_free
            else f"~${self._backend.cost_per_1000_pages:.2f}/1000 pages",
        )
        table.add_row("Total requested", str(len(pages)))
        table.add_row("Already completed", str(len(state.completed_pages)))
        table.add_row("Pending", str(len(pending)))

        console.print(table)

    def _write_output(
        self,
        pdf_path: Path,
        results: dict[int, str],
        output_file: Path,
        pages: list[int],
    ) -> None:
        """Write OCR results to markdown file."""
        import re

        existing_results: dict[int, str] = {}
        if output_file.exists():
            content = output_file.read_text(encoding="utf-8")
            for match in re.finditer(
                r"## Page (\d+)\n\n(.*?)(?=\n---|\Z)", content, re.DOTALL
            ):
                page_num = int(match.group(1))
                text = match.group(2).strip()
                existing_results[page_num] = text

        all_results = {**existing_results, **results}
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sorted_pages = sorted(all_results.keys())

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# {pdf_path.stem} - OCR Output\n")
            f.write(f"Generated: {timestamp}\n")
            f.write(f"Backend: {self._backend.name}\n")
            f.write(f"Pages processed: {len(sorted_pages)}\n\n")
            f.write("---\n\n")

            for page_num in sorted_pages:
                f.write(f"## Page {page_num}\n\n")
                f.write(all_results[page_num])
                f.write("\n\n---\n\n")

    def cleanup(self) -> None:
        """Cleanup backend resources."""
        if self._backend:
            self._backend.cleanup()


def _convert_page(
    pdf_path: str, page_num: int, dpi: int, temp_dir: str
) -> Optional[str]:
    """Convert a single PDF page to image (runs in separate process)."""
    try:
        images = convert_from_path(
            pdf_path,
            dpi=dpi,
            first_page=page_num,
            last_page=page_num,
            fmt="png",
        )

        if images:
            output_path = Path(temp_dir) / f"page_{page_num}.png"
            images[0].save(output_path, "PNG")
            return str(output_path)

        return None
    except Exception as e:
        logger.error(f"Error converting page {page_num}: {e}")
        return None
