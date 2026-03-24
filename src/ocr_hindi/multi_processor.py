"""Multi-backend OCR processor supporting various engines.

Allows switching between Gemini, Marker, EasyOCR, Tesseract, and Hybrid modes.

Features:

- File-based cache for crash recovery (no data loss on crash)
- Graceful shutdown on Ctrl+C (saves all completed work)
- Memory-efficient processing (cleanup after each page)
- Resume capability (skip already cached pages)
"""

from __future__ import annotations

import asyncio
import gc
import logging
import signal
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

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
from rich.table import Table

from .backends import OCRBackend, OCRResult, get_backend
from .backends.base import BackendConfig
from .cache import OCRCache
from .utils import (
    ProgressState,
    format_duration,
    get_log_file,
    get_output_file,
    get_progress_file,
    write_markdown_output,
)

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class MultiProcessorConfig:
    """Configuration for multi-backend processor."""

    backend: str = "hybrid"
    dpi: int = 200
    max_concurrent: int = 10
    confidence_threshold: float = 0.85
    detect_mantras: bool = True
    gemini_model: str = "gemini-2.0-flash"


class MultiBackendProcessor:
    """OCR processor supporting multiple backends.

    Usage::

        processor = MultiBackendProcessor(config)
        processor.initialize()
        success, failed, output = processor.process_pdf(pdf_path, pages)
    """

    def __init__(self, config: MultiProcessorConfig | None = None) -> None:
        self.config = config or MultiProcessorConfig()
        self._backend: OCRBackend | None = None
        self._initialized = False

    def initialize(self, quiet: bool = False) -> tuple[bool, str, str]:
        """Initialize the selected backend.

        Args:
            quiet: If True, suppress verbose initialization output.

        Returns:
            Tuple of (success, backend_name, message).
        """
        if not quiet:
            logger.info("Initializing %s backend...", self.config.backend)

        try:
            backend_config = BackendConfig(
                dpi=self.config.dpi,
                confidence_threshold=self.config.confidence_threshold,
                detect_mantras=self.config.detect_mantras,
            )

            backend_kwargs: dict = {"config": backend_config}

            if self.config.backend == "gemini":
                backend_kwargs["model"] = self.config.gemini_model
            elif self.config.backend == "hybrid":
                backend_kwargs["confidence_threshold"] = (
                    self.config.confidence_threshold
                )
                backend_kwargs["verify_mantras"] = self.config.detect_mantras
                backend_kwargs["gemini_model"] = self.config.gemini_model

            self._backend = get_backend(self.config.backend, **backend_kwargs)

            if hasattr(self._backend, "set_quiet"):
                self._backend.set_quiet(quiet)

            success, message = self._backend.initialize()

            if success:
                self._initialized = True

            return success, self._backend.name, message

        except Exception as exc:
            return False, "error", str(exc)

    def process_pdf(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
        output_dir: Path | None = None,
    ) -> tuple[int, int, Path]:
        """Process PDF with the configured backend (synchronous).

        Args:
            pdf_path: Path to PDF file.
            pages: List of page numbers to process (1-indexed).
            resume: Whether to resume from previous progress.
            dry_run: Only show what would be processed.
            output_dir: If provided, write output files here.

        Returns:
            Tuple of (successful_count, failed_count, output_path).

        Raises:
            RuntimeError: If processor not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Processor not initialized. Call initialize() first.")

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_file = get_output_file(pdf_path, output_dir)
        log_file = get_log_file(pdf_path, output_dir)
        progress_file = get_progress_file(pdf_path, output_dir)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        state = self._load_or_create_state(pdf_path, pages, resume, progress_file)
        pending_pages = state.get_pending_pages(pages)

        if dry_run:
            self._print_dry_run(pdf_path, pages, state, pending_pages)
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All pages already processed![/green]")
            return len(state.completed_pages), len(state.failed_pages), output_file

        console.print(
            f"\n[bold]Processing {len(pending_pages)} pages "
            f"with {self._backend.name}...[/bold]"
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

                    images = convert_from_path(
                        pdf_path,
                        dpi=self.config.dpi,
                        first_page=page_num,
                        last_page=page_num,
                        fmt="png",
                    )

                    if not images:
                        logger.error("Page %d: Failed to convert to image", page_num)
                        state.mark_failed(page_num)
                        progress.advance(task)
                        continue

                    result = self._backend.process_image(images[0], page_num)

                    if result.success:
                        results[page_num] = result.text
                        state.mark_completed(page_num)
                        logger.info(
                            "Page %d: %d chars, confidence: %.0f%%, backend: %s",
                            page_num,
                            len(result.text),
                            result.confidence * 100,
                            result.backend_used,
                        )
                    else:
                        state.mark_failed(page_num)
                        logger.error("Page %d: %s", page_num, result.error)

                    state.save(progress_file)
                    progress.advance(task)

                except KeyboardInterrupt:
                    console.print(
                        "\n[yellow]Interrupted! Saving progress...[/yellow]"
                    )
                    state.save(progress_file)
                    raise

                except Exception as exc:
                    logger.error("Page %d: Unexpected error - %s", page_num, exc)
                    state.mark_failed(page_num)
                    state.save(progress_file)
                    progress.advance(task)

        write_markdown_output(
            pdf_path, results, output_file, backend_name=self._backend.name
        )

        total_time = time.time() - start_time
        logger.info(
            "Complete: %d success, %d failed, %s",
            len(state.completed_pages),
            len(state.failed_pages),
            format_duration(total_time),
        )

        self._print_backend_stats()

        return len(state.completed_pages), len(state.failed_pages), output_file

    async def process_pdf_async(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
        output_dir: Path | None = None,
    ) -> tuple[int, int, Path]:
        """Async version of process_pdf with crash recovery and graceful shutdown.

        Features:

        - File-based cache: Each page saved to disk immediately (crash-safe)
        - Graceful shutdown: Ctrl+C saves all completed work
        - Memory efficient: Images cleaned up after each page
        - Resume capable: Skips already cached pages

        Args:
            pdf_path: Path to PDF file.
            pages: List of page numbers to process (1-indexed).
            resume: Whether to resume from previous progress.
            dry_run: Only show what would be processed.
            output_dir: If provided, write output files here.

        Returns:
            Tuple of (successful_count, failed_count, output_path).

        Raises:
            RuntimeError: If processor not initialized.
        """
        if not self._initialized:
            raise RuntimeError("Processor not initialized. Call initialize() first.")

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        output_file = get_output_file(pdf_path, output_dir)
        log_file = get_log_file(pdf_path, output_dir)
        progress_file = get_progress_file(pdf_path, output_dir)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

        cache = OCRCache(pdf_path, output_dir)

        shutdown_requested = asyncio.Event()

        def handle_shutdown(signum, frame):
            """Handle shutdown signals gracefully."""
            console.print("\n[yellow]Shutdown requested, saving work...[/yellow]")
            shutdown_requested.set()

        original_sigint = signal.signal(signal.SIGINT, handle_shutdown)
        original_sigterm = signal.signal(signal.SIGTERM, handle_shutdown)

        state = self._load_or_create_state(pdf_path, pages, resume, progress_file)

        # Sync cache with state for crash recovery
        cached_pages = set(cache.pages())
        if resume and cached_pages:
            for page in cached_pages:
                if page not in state.completed_pages:
                    state.mark_completed(page)
            console.print(f"[yellow]Found {len(cached_pages)} pages in cache[/yellow]")

        pending_pages = state.get_pending_pages(pages)
        pending_pages = [p for p in pending_pages if p not in cached_pages]

        if dry_run:
            self._print_dry_run(pdf_path, pages, state, pending_pages)
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All pages already processed![/green]")
            self._finalize(cache, state, output_file, pdf_path)
            return len(state.completed_pages), len(state.failed_pages), output_file

        results: dict[int, str] = {}
        start_time = time.time()

        temp_dir = Path(tempfile.mkdtemp(prefix="ocr_multi_"))
        image_paths: dict[int, Path] = {}

        try:
            image_paths = await self._convert_pages_async(
                pdf_path, pending_pages, temp_dir
            )

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
                        loop = asyncio.get_running_loop()
                        return await loop.run_in_executor(
                            None,
                            lambda: self._backend.process_image(image, page_num),
                        )
                    finally:
                        if image:
                            image.close()
                            del image
                        if page_num in image_paths:
                            image_paths[page_num].unlink(missing_ok=True)
                        if page_num % 10 == 0:
                            gc.collect()

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TimeRemainingColumn(),
                console=console,
            ) as progress:
                task = progress.add_task(
                    "OCR Processing", total=len(pending_pages)
                )

                tasks = [process_page(pn) for pn in pending_pages]

                for coro in asyncio.as_completed(tasks):
                    if shutdown_requested.is_set():
                        console.print(
                            "[yellow]Completing current tasks...[/yellow]"
                        )
                        break

                    result = await coro

                    if result.success:
                        cache.save(
                            result.page_num,
                            result.text,
                            backend=result.backend_used,
                            confidence=result.confidence,
                        )
                        results[result.page_num] = result.text
                        state.mark_completed(result.page_num)
                        logger.info(
                            "Page %d: %d chars [cached to disk]",
                            result.page_num,
                            len(result.text),
                        )
                    elif result.error != "Shutdown requested":
                        state.mark_failed(result.page_num)
                        logger.error(
                            "Page %d: %s", result.page_num, result.error
                        )

                    state.save(progress_file)
                    progress.advance(task)

        finally:
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

            for path in image_paths.values():
                path.unlink(missing_ok=True)
            try:
                temp_dir.rmdir()
            except OSError:
                pass
            gc.collect()

        self._finalize(cache, state, output_file, pdf_path)

        total_time = time.time() - start_time
        logger.info(
            "Complete: %d success, %d failed, %s",
            len(state.completed_pages),
            len(state.failed_pages),
            format_duration(total_time),
        )

        self._print_backend_stats()

        if shutdown_requested.is_set():
            console.print(
                f"[green]Saved {len(state.completed_pages)} pages "
                f"before shutdown[/green]"
            )
            console.print("[dim]  Resume with: --resume flag[/dim]")

        return len(state.completed_pages), len(state.failed_pages), output_file

    # --- Internal helpers ---

    def _load_or_create_state(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool,
        progress_file: Path,
    ) -> ProgressState:
        """Load existing progress state or create a new one.

        Args:
            pdf_path: Path to the PDF being processed.
            pages: Requested page numbers.
            resume: Whether to try loading existing state.
            progress_file: Path to the progress file.

        Returns:
            ProgressState instance.
        """
        state: ProgressState | None = None
        if resume:
            state = ProgressState.load(progress_file)
            if state:
                console.print(
                    f"[yellow]Resuming: {len(state.completed_pages)} "
                    f"pages done[/yellow]"
                )

        if not state:
            state = ProgressState(pdf_path=str(pdf_path), total_pages=max(pages))

        return state

    def _finalize(
        self,
        cache: OCRCache,
        state: ProgressState,
        output_file: Path,
        pdf_path: Path,
    ) -> None:
        """Finalize processing: merge cache to output file.

        Called after normal completion, graceful shutdown, or when
        resuming with all pages cached.

        Args:
            cache: The OCR cache to read results from.
            state: Current progress state.
            output_file: Path to the output markdown file.
            pdf_path: Path to the source PDF.
        """
        cached_results = cache.all_results()

        if not cached_results:
            logger.warning("No cached results to finalize")
            return

        write_markdown_output(
            pdf_path,
            cached_results,
            output_file,
            backend_name=self._backend.name if self._backend else "",
        )

        logger.info("Finalized %d pages to %s", len(cached_results), output_file)
        console.print(
            f"[green]Saved {len(cached_results)} pages to {output_file}[/green]"
        )

    async def _convert_pages_async(
        self,
        pdf_path: Path,
        pages: list[int],
        temp_dir: Path,
    ) -> dict[int, Path]:
        """Convert PDF pages to images asynchronously.

        Args:
            pdf_path: Path to the PDF file.
            pages: Page numbers to convert.
            temp_dir: Directory for temporary image files.

        Returns:
            Dict mapping page numbers to image file paths.
        """
        image_paths: dict[int, Path] = {}
        loop = asyncio.get_running_loop()

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
                except Exception as exc:
                    logger.error("Failed to convert page %d: %s", page_num, exc)

        return image_paths

    def _print_dry_run(
        self,
        pdf_path: Path,
        pages: list[int],
        state: ProgressState,
        pending: list[int],
    ) -> None:
        """Print dry run information.

        Args:
            pdf_path: Path to the PDF file.
            pages: All requested pages.
            state: Current progress state.
            pending: Pages still to process.
        """
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

    def _print_backend_stats(self) -> None:
        """Print backend-specific stats if available."""
        if hasattr(self._backend, "print_stats"):
            self._backend.print_stats()
        elif hasattr(self._backend, "print_cost_summary"):
            self._backend.print_cost_summary()

    def cleanup(self) -> None:
        """Cleanup backend resources."""
        if self._backend:
            self._backend.cleanup()


def _convert_page(
    pdf_path: str, page_num: int, dpi: int, temp_dir: str
) -> str | None:
    """Convert a single PDF page to image (runs in separate process).

    Args:
        pdf_path: Path to the PDF file.
        page_num: 1-indexed page number.
        dpi: Resolution for rendering.
        temp_dir: Directory for the output image.

    Returns:
        Path to the saved image, or None on failure.
    """
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
    except Exception as exc:
        logging.getLogger(__name__).error(
            "Error converting page %d: %s", page_num, exc
        )
        return None
