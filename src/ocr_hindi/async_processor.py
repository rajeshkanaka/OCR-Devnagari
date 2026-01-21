"""
High-performance async OCR processor with concurrent workers and pipeline architecture.

Performance optimizations:
1. Async I/O with semaphore-based rate limiting
2. Pre-batch image conversion using multiprocessing
3. Pipeline architecture separating CPU-bound and I/O-bound work
4. Token bucket rate limiting for burst + sustained throughput
"""

import asyncio
import logging
import os
import tempfile
import time
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import AsyncIterator, Optional

from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
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
)

load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class AsyncOCRConfig:
    """Configuration for async OCR processing"""

    model: str = "gemini-3-flash-preview"
    dpi: int = 200
    max_concurrent: int = 10  # Concurrent API requests
    requests_per_minute: int = 60  # Vertex AI typical limit
    max_retries: int = 3
    retry_base_delay: float = 1.0
    image_batch_size: int = 20  # Pages to pre-convert at once
    image_workers: int = 4  # Parallel image conversion processes


@dataclass
class PageResult:
    """Result of processing a single page"""

    page_num: int
    text: str = ""
    success: bool = False
    error: Optional[str] = None
    duration: float = 0.0


class TokenBucket:
    """
    Token bucket rate limiter for smooth rate limiting with burst capability.

    Allows burst of requests up to bucket size, then refills at steady rate.
    """

    def __init__(self, rate: float, capacity: int):
        """
        Args:
            rate: Tokens per second to add
            capacity: Maximum bucket size (burst capacity)
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = capacity
        self.last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> float:
        """
        Acquire tokens, waiting if necessary.

        Returns:
            Time waited in seconds
        """
        async with self._lock:
            wait_time = 0.0

            # Refill tokens based on time elapsed
            now = time.monotonic()
            elapsed = now - self.last_update
            self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
            self.last_update = now

            # Wait if not enough tokens
            if self.tokens < tokens:
                deficit = tokens - self.tokens
                wait_time = deficit / self.rate
                await asyncio.sleep(wait_time)
                self.tokens = 0
            else:
                self.tokens -= tokens

            return wait_time


class AsyncOCRProcessor:
    """
    High-performance async OCR processor.

    Features:
    - Concurrent API requests with semaphore limiting
    - Token bucket rate limiting for smooth throughput
    - Pre-batch image conversion using multiprocessing
    - Graceful shutdown with progress preservation
    """

    def __init__(self, config: Optional[AsyncOCRConfig] = None):
        self.config = config or AsyncOCRConfig()
        self.client = None
        self._rate_limiter = TokenBucket(
            rate=self.config.requests_per_minute / 60.0,  # Convert to per-second
            capacity=min(10, self.config.max_concurrent),  # Burst capacity
        )
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._shutdown = False

    def validate_auth(self) -> tuple[bool, str, str]:
        """Validate authentication and initialize client."""
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
                # Test connection
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

        except Exception as e:
            return False, "Error", f"Authentication failed: {str(e)}"

    async def _process_single_page(self, image_path: Path, page_num: int) -> PageResult:
        """Process a single page with rate limiting and retries."""
        from google.genai import types
        from PIL import Image

        start_time = time.monotonic()

        for attempt in range(self.config.max_retries):
            if self._shutdown:
                return PageResult(
                    page_num=page_num, error="Shutdown requested", duration=0
                )

            try:
                # Acquire rate limit token
                await self._rate_limiter.acquire()

                # Acquire concurrency semaphore
                async with self._semaphore:
                    # Load image
                    image = Image.open(image_path)

                    # Make API call (sync, but wrapped in executor for non-blocking)
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None,
                        lambda: self.client.models.generate_content(
                            model=self.config.model, contents=[image, OCR_PROMPT]
                        ),
                    )

                    text = response.text.strip() if response.text else ""
                    duration = time.monotonic() - start_time

                    logger.info(
                        f"Page {page_num}: {len(text)} chars in {duration:.1f}s"
                    )

                    return PageResult(
                        page_num=page_num,
                        text=text,
                        success=True,
                        duration=duration,
                    )

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"Page {page_num}, attempt {attempt + 1}: {error_msg}")

                if "429" in error_msg or "quota" in error_msg.lower():
                    # Rate limit - exponential backoff with longer wait
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
        on_progress: Optional[callable] = None,
    ) -> tuple[int, int, Path]:
        """
        Process PDF with high-performance async pipeline.

        Pipeline stages:
        1. Pre-convert pages to images (multiprocess, CPU-bound)
        2. Process images through API (async, I/O-bound)
        3. Write results to output file

        Args:
            pdf_path: Path to PDF file
            pages: List of page numbers (1-indexed)
            resume: Resume from previous progress
            dry_run: Only show what would be processed
            on_progress: Callback for progress updates

        Returns:
            Tuple of (successful_count, failed_count, output_path)
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call validate_auth() first.")

        self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
        self._shutdown = False

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

        console.print(f"\n[bold]Processing {len(pending_pages)} pages[/bold]")
        console.print(f"  Concurrent workers: {self.config.max_concurrent}")
        console.print(f"  Rate limit: {self.config.requests_per_minute} RPM")
        console.print(f"  Log: {log_file}")

        results: dict[int, str] = {}
        start_time = time.monotonic()

        # Create progress display
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TextColumn("•"),
            TimeElapsedColumn(),
            TextColumn("•"),
            TimeRemainingColumn(),
            console=console,
        )

        with progress:
            # Stage 1: Pre-convert images
            convert_task = progress.add_task(
                "[cyan]Converting PDF pages...", total=len(pending_pages)
            )

            image_paths = await self._batch_convert_images(
                pdf_path, pending_pages, progress, convert_task
            )

            progress.update(convert_task, visible=False)

            # Stage 2: Process images through API
            ocr_task = progress.add_task(
                "[green]OCR Processing...", total=len(pending_pages)
            )

            try:
                # Process all pages concurrently
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
                        logger.error(f"Page {result.page_num}: {result.error}")

                    state.save(progress_file)
                    progress.advance(ocr_task)

            except asyncio.CancelledError:
                console.print("\n[yellow]Cancelled! Saving progress...[/yellow]")
                state.save(progress_file)
                raise

            finally:
                # Cleanup temp images
                for path in image_paths.values():
                    try:
                        path.unlink()
                    except Exception:
                        pass

        # Write output
        self._write_output(pdf_path, results, output_file, pages)

        total_time = time.monotonic() - start_time
        logger.info(
            f"Complete: {len(state.completed_pages)} success, "
            f"{len(state.failed_pages)} failed, {format_duration(total_time)}"
        )

        return len(state.completed_pages), len(state.failed_pages), output_file

    async def _batch_convert_images(
        self,
        pdf_path: Path,
        pages: list[int],
        progress: Progress,
        task_id: TaskID,
    ) -> dict[int, Path]:
        """
        Convert PDF pages to images using multiprocessing.

        Returns:
            Dict mapping page numbers to image file paths
        """
        from pdf2image import convert_from_path

        image_paths: dict[int, Path] = {}
        temp_dir = Path(tempfile.mkdtemp(prefix="ocr_hindi_"))

        # Process in batches to manage memory
        batch_size = self.config.image_batch_size

        for i in range(0, len(pages), batch_size):
            batch = pages[i : i + batch_size]

            # Convert batch using process pool
            loop = asyncio.get_event_loop()

            with ProcessPoolExecutor(max_workers=self.config.image_workers) as executor:
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
                    except Exception as e:
                        logger.error(f"Failed to convert page {page_num}: {e}")
                        progress.advance(task_id)

        return image_paths

    def _print_dry_run(
        self,
        pdf_path: Path,
        pages: list[int],
        state: ProgressState,
        pending: list[int],
    ) -> None:
        """Print dry run information."""
        table = Table(title="Dry Run - Processing Plan")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("PDF", str(pdf_path))
        table.add_row("Total requested", str(len(pages)))
        table.add_row("Already completed", str(len(state.completed_pages)))
        table.add_row("Pending", str(len(pending)))
        table.add_row("Concurrent workers", str(self.config.max_concurrent))
        table.add_row("Rate limit", f"{self.config.requests_per_minute} RPM")

        # Estimate time with concurrency
        effective_rate = min(
            self.config.max_concurrent * 12,  # ~12 pages/min per worker (5s each)
            self.config.requests_per_minute,
        )
        estimated_minutes = len(pending) / effective_rate
        table.add_row("Estimated time", f"~{estimated_minutes:.1f} minutes")

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
            f.write(f"Pages processed: {len(sorted_pages)}\n\n")
            f.write("---\n\n")

            for page_num in sorted_pages:
                f.write(f"## Page {page_num}\n\n")
                f.write(all_results[page_num])
                f.write("\n\n---\n\n")

    def request_shutdown(self) -> None:
        """Request graceful shutdown."""
        self._shutdown = True


def _convert_single_page(
    pdf_path: str, page_num: int, dpi: int, temp_dir: str
) -> Optional[str]:
    """
    Convert a single PDF page to image.

    This function runs in a separate process.
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

    except Exception as e:
        logger.error(f"Error converting page {page_num}: {e}")
        return None


# Convenience function for running async processor
def run_async_ocr(
    pdf_path: Path,
    pages: list[int],
    config: Optional[AsyncOCRConfig] = None,
    resume: bool = False,
    dry_run: bool = False,
) -> tuple[int, int, Path]:
    """
    Run async OCR processor.

    Convenience wrapper that handles the event loop.
    """
    processor = AsyncOCRProcessor(config=config)

    success, auth_method, message = processor.validate_auth()
    if not success:
        raise RuntimeError(f"Authentication failed: {message}")

    console.print(f"[green]✓[/green] {auth_method}: {message}")

    return asyncio.run(
        processor.process_pdf(pdf_path, pages, resume=resume, dry_run=dry_run)
    )
