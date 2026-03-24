"""High-performance async OCR processor with concurrent workers and pipeline architecture.

Performance optimizations:

1. Async I/O with semaphore-based rate limiting
2. Pre-batch image conversion using multiprocessing
3. Pipeline architecture separating CPU-bound and I/O-bound work
4. Token bucket rate limiting for burst + sustained throughput
"""

from __future__ import annotations

import asyncio
import logging
import os
import tempfile
import time
from collections.abc import Callable
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from pathlib import Path

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)
from rich.table import Table

from .prompts import OCR_PROMPT
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
class AsyncOCRConfig:
    """Configuration for async OCR processing."""

    model: str = "gemini-2.0-flash"
    dpi: int = 200
    max_concurrent: int = 10
    requests_per_minute: int = 60
    max_retries: int = 3
    retry_base_delay: float = 1.0
    image_batch_size: int = 20
    image_workers: int = 4


@dataclass
class PageResult:
    """Result of processing a single page."""

    page_num: int
    text: str = ""
    success: bool = False
    error: str | None = None
    duration: float = 0.0


class TokenBucket:
    """Token bucket rate limiter for smooth rate limiting with burst capability.

    Allows burst of requests up to bucket size, then refills at steady rate.
    """

    def __init__(self, rate: float, capacity: int) -> None:
        """Initialize the token bucket.

        Args:
            rate: Tokens per second to add.
            capacity: Maximum bucket size (burst capacity).
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """Acquire tokens, waiting if necessary.

        Args:
            tokens: Number of tokens to acquire.

        Returns:
            Time waited in seconds.
        """
        async with self._lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            wait_time = 0.0
            if self.tokens < tokens:
                deficit = tokens - self.tokens
                wait_time = deficit / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens

            return wait_time


class AsyncOCRProcessor:
    """High-performance async OCR processor.

    Features:

    - Concurrent API requests with semaphore limiting
    - Token bucket rate limiting for smooth throughput
    - Pre-batch image conversion using multiprocessing
    - Graceful shutdown with progress preservation
    """

    def __init__(self, config: AsyncOCRConfig | None = None) -> None:
        self.config = config or AsyncOCRConfig()
        self.client = None
        self._rate_limiter = TokenBucket(
            rate=self.config.requests_per_minute / 60.0,
            capacity=min(10, self.config.max_concurrent),
        )
        self._semaphore: asyncio.Semaphore | None = None
        self._shutdown = False

    def validate_auth(self) -> tuple[bool, str, str]:
        """Validate authentication and initialize client.

        Returns:
            Tuple of (success, auth_method, message).
        """
        try:
            from google import genai

            use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in (
                "1",
                "true",
                "yes",
            )
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

            if use_vertex and project:
                self.client = genai.Client(
                    vertexai=True, project=project, location=location
                )
                response = self.client.models.generate_content(
                    model=self.config.model, contents="Say 'OK'"
                )
                if response.text:
                    return (
                        True,
                        "Vertex AI",
                        f"Project: {project}, Location: {location}",
                    )

            api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
            if api_key:
                self.client = genai.Client(api_key=api_key)
                response = self.client.models.generate_content(
                    model=self.config.model, contents="Say 'OK'"
                )
                if response.text:
                    return True, "Gemini API", "Using API key"

            return False, "None", "No valid authentication found"

        except Exception as exc:
            return False, "Error", f"Authentication failed: {exc}"

    async def _process_single_page(
        self, image_path: Path, page_num: int
    ) -> PageResult:
        """Process a single page with rate limiting and retries.

        Args:
            image_path: Path to the page image file.
            page_num: 1-indexed page number.

        Returns:
            PageResult with extracted text.
        """
        from PIL import Image

        start_time = time.monotonic()

        for attempt in range(self.config.max_retries):
            if self._shutdown:
                return PageResult(
                    page_num=page_num, error="Shutdown requested", duration=0
                )

            try:
                await self._rate_limiter.acquire()

                async with self._semaphore:
                    image = Image.open(image_path)

                    loop = asyncio.get_running_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=self.config.model,
                            contents=[image, OCR_PROMPT],
                        ),
                    )

                    text = response.text.strip() if response.text else ""
                    duration = time.monotonic() - start_time

                    logger.info(
                        "Page %d: %d chars in %.1fs", page_num, len(text), duration
                    )

                    return PageResult(
                        page_num=page_num,
                        text=text,
                        success=True,
                        duration=duration,
                    )

            except Exception as exc:
                error_msg = str(exc)
                logger.warning(
                    "Page %d, attempt %d: %s", page_num, attempt + 1, error_msg
                )

                if "429" in error_msg or "quota" in error_msg.lower():
                    delay = self.config.retry_base_delay * (3**attempt)
                    await asyncio.sleep(delay)
                elif attempt < self.config.max_retries - 1:
                    delay = self.config.retry_base_delay * (2**attempt)
                    await asyncio.sleep(delay)

        duration = time.monotonic() - start_time
        return PageResult(
            page_num=page_num,
            error=f"Failed after {self.config.max_retries} attempts",
            duration=duration,
        )

    async def process_pdf(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
        on_progress: Callable[[str], None] | None = None,
    ) -> tuple[int, int, Path]:
        """Process PDF with high-performance async pipeline.

        Pipeline stages:

        1. Pre-convert pages to images (multiprocess, CPU-bound)
        2. Process images through API (async, I/O-bound)
        3. Write results to output file

        Args:
            pdf_path: Path to PDF file.
            pages: List of page numbers (1-indexed).
            resume: Resume from previous progress.
            dry_run: Only show what would be processed.
            on_progress: Callback for progress updates.

        Returns:
            Tuple of (successful_count, failed_count, output_path).

        Raises:
            RuntimeError: If client not initialized.
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call validate_auth() first.")

        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._shutdown = False

        progress_file = get_progress_file(pdf_path)
        output_file = get_output_file(pdf_path)
        log_file = get_log_file(pdf_path)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setFormatter(
            logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        )
        logger.addHandler(file_handler)
        logger.setLevel(logging.DEBUG)

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

        pending_pages = state.get_pending_pages(pages)

        if dry_run:
            self._print_dry_run(pdf_path, pages, state, pending_pages)
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All pages already processed![/green]")
            return len(state.completed_pages), len(state.failed_pages), output_file

        console.print(f"\n[bold]Processing {len(pending_pages)} pages[/bold]")
        console.print(f"  Concurrent workers: {self.config.max_concurrent}")
        console.print(f"  Rate limit: {self.config.requests_per_minute} RPM")
        console.print(f"  Log: {log_file}")

        results: dict[int, str] = {}
        start_time = time.monotonic()

        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("-"),
            TimeElapsedColumn(),
            TextColumn("-"),
            TimeRemainingColumn(),
            console=console,
        )

        with progress:
            convert_task = progress.add_task(
                "[cyan]Converting PDF pages...", total=len(pending_pages)
            )

            image_paths = await self._batch_convert_images(
                pdf_path, pending_pages, progress, convert_task
            )

            progress.update(convert_task, visible=False)

            ocr_task = progress.add_task(
                "[green]OCR Processing...", total=len(pending_pages)
            )

            try:
                tasks = [
                    self._process_single_page(image_paths[page_num], page_num)
                    for page_num in pending_pages
                    if page_num in image_paths
                ]

                for coro in asyncio.as_completed(tasks):
                    result = await coro

                    if result.success:
                        results[result.page_num] = result.text
                        state.mark_completed(result.page_num)
                    else:
                        state.mark_failed(result.page_num)
                        logger.error(
                            "Page %d: %s", result.page_num, result.error
                        )

                    state.save(progress_file)
                    progress.advance(ocr_task)

            except asyncio.CancelledError:
                console.print("\n[yellow]Cancelled! Saving progress...[/yellow]")
                state.save(progress_file)
                raise

            finally:
                for path in image_paths.values():
                    path.unlink(missing_ok=True)

        write_markdown_output(pdf_path, results, output_file)

        total_time = time.monotonic() - start_time
        logger.info(
            "Complete: %d success, %d failed, %s",
            len(state.completed_pages),
            len(state.failed_pages),
            format_duration(total_time),
        )

        return len(state.completed_pages), len(state.failed_pages), output_file

    async def _batch_convert_images(
        self,
        pdf_path: Path,
        pages: list[int],
        progress: Progress,
        task_id: TaskID,
    ) -> dict[int, Path]:
        """Convert PDF pages to images using multiprocessing.

        Args:
            pdf_path: Path to the PDF file.
            pages: Page numbers to convert.
            progress: Rich progress display.
            task_id: Progress task ID for updates.

        Returns:
            Dict mapping page numbers to image file paths.
        """
        from pdf2image import convert_from_path as _  # noqa: F401 (ensure available)

        image_paths: dict[int, Path] = {}
        temp_dir = Path(tempfile.mkdtemp(prefix="ocr_hindi_"))
        batch_size = self.config.image_batch_size

        for i in range(0, len(pages), batch_size):
            batch = pages[i : i + batch_size]
            loop = asyncio.get_running_loop()

            with ProcessPoolExecutor(
                max_workers=self.config.image_workers
            ) as executor:
                futures = []
                for page_num in batch:
                    future = loop.run_in_executor(
                        executor,
                        _convert_single_page,
                        str(pdf_path),
                        page_num,
                        self.config.dpi,
                        str(temp_dir),
                    )
                    futures.append((page_num, future))

                for page_num, future in futures:
                    try:
                        image_path = await future
                        if image_path:
                            image_paths[page_num] = Path(image_path)
                        progress.advance(task_id)
                    except Exception as exc:
                        logger.error(
                            "Failed to convert page %d: %s", page_num, exc
                        )
                        progress.advance(task_id)

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
        table.add_row("Total requested", str(len(pages)))
        table.add_row("Already completed", str(len(state.completed_pages)))
        table.add_row("Pending", str(len(pending)))
        table.add_row("Concurrent workers", str(self.config.max_concurrent))
        table.add_row("Rate limit", f"{self.config.requests_per_minute} RPM")

        effective_rate = min(
            self.config.max_concurrent * 12,
            self.config.requests_per_minute,
        )
        estimated_minutes = len(pending) / effective_rate
        table.add_row("Estimated time", f"~{estimated_minutes:.1f} minutes")

        console.print(table)

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown = True


def _convert_single_page(
    pdf_path: str, page_num: int, dpi: int, temp_dir: str
) -> str | None:
    """Convert a single PDF page to image.

    This function runs in a separate process.

    Args:
        pdf_path: Path to the PDF file.
        page_num: 1-indexed page number.
        dpi: Resolution for rendering.
        temp_dir: Directory for the output image.

    Returns:
        Path to the saved image, or None on failure.
    """
    from pdf2image import convert_from_path

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


def run_async_ocr(
    pdf_path: Path,
    pages: list[int],
    config: AsyncOCRConfig | None = None,
    resume: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, Path]:
    """Run async OCR processor (convenience wrapper).

    Handles the event loop setup.

    Args:
        pdf_path: Path to the PDF file.
        pages: List of page numbers (1-indexed).
        config: Optional async OCR configuration.
        resume: Whether to resume from previous progress.
        dry_run: Only show what would be processed.

    Returns:
        Tuple of (successful_count, failed_count, output_path).

    Raises:
        RuntimeError: If authentication fails.
    """
    processor = AsyncOCRProcessor(config=config)

    success, auth_method, message = processor.validate_auth()
    if not success:
        raise RuntimeError(f"Authentication failed: {message}")

    console.print(f"[green]{auth_method}: {message}[/green]")

    return asyncio.run(
        processor.process_pdf(pdf_path, pages, resume=resume, dry_run=dry_run)
    )
