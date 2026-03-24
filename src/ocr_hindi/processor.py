"""Core OCR processing logic using Gemini + Vertex AI."""

from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path

from pdf2image import convert_from_path
from PIL import Image
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
class ProcessingResult:
    """Result of processing a single page."""

    page_num: int
    text: str
    success: bool
    error: str | None = None
    duration: float = 0.0


@dataclass
class OCRConfig:
    """Configuration for OCR processing."""

    model: str = "gemini-2.0-flash"
    dpi: int = 200
    rate_limit: int = 15
    max_retries: int = 3
    retry_base_delay: float = 2.0


class OCRProcessor:
    """Handles OCR processing of PDF files using Gemini.

    This is the original single-backend processor using Gemini Vision API.
    For multi-backend support, use MultiBackendProcessor instead.
    """

    def __init__(self, config: OCRConfig | None = None) -> None:
        self.config = config or OCRConfig()
        self.client = None
        self._last_request_time = 0.0
        self._min_request_interval = 60.0 / self.config.rate_limit

    def validate_auth(self) -> tuple[bool, str, str]:
        """Validate authentication and return status.

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
                    return True, "Gemini API", "Using API key from environment"

            return (
                False,
                "None",
                "No valid authentication found. Set "
                "GOOGLE_GENAI_USE_VERTEXAI=1 with GOOGLE_CLOUD_PROJECT, "
                "or set GEMINI_API_KEY",
            )

        except Exception as exc:
            return False, "Error", f"Authentication failed: {exc}"

    def _enforce_rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _process_single_page(
        self, image: Image.Image, page_num: int
    ) -> ProcessingResult:
        """Process a single page image with retries.

        Args:
            image: PIL Image of the page.
            page_num: 1-indexed page number.

        Returns:
            ProcessingResult with extracted text.
        """
        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                self._enforce_rate_limit()

                response = self.client.models.generate_content(
                    model=self.config.model, contents=[image, OCR_PROMPT]
                )

                text = response.text.strip() if response.text else ""
                duration = time.time() - start_time

                logger.info("Page %d: Extracted %d characters", page_num, len(text))

                return ProcessingResult(
                    page_num=page_num, text=text, success=True, duration=duration
                )

            except Exception as exc:
                error_msg = str(exc)
                logger.warning(
                    "Page %d, attempt %d/%d: %s",
                    page_num,
                    attempt + 1,
                    self.config.max_retries,
                    error_msg,
                )

                if "429" in error_msg or "quota" in error_msg.lower():
                    delay = self.config.retry_base_delay * (2**attempt) * 2
                    logger.info("Rate limited. Waiting %.1fs before retry...", delay)
                    time.sleep(delay)
                elif attempt < self.config.max_retries - 1:
                    delay = self.config.retry_base_delay * (2**attempt)
                    time.sleep(delay)

        duration = time.time() - start_time
        return ProcessingResult(
            page_num=page_num,
            text="",
            success=False,
            error=f"Failed after {self.config.max_retries} attempts",
            duration=duration,
        )

    def process_pdf(
        self,
        pdf_path: Path,
        pages: list[int],
        resume: bool = False,
        dry_run: bool = False,
        output_dir: Path | None = None,
    ) -> tuple[int, int, Path]:
        """Process specified pages from a PDF file.

        Args:
            pdf_path: Path to the PDF file.
            pages: List of page numbers to process (1-indexed).
            resume: Whether to resume from previous progress.
            dry_run: If True, only show what would be processed.
            output_dir: If provided, write output files here.

        Returns:
            Tuple of (successful_count, failed_count, output_path).

        Raises:
            RuntimeError: If client not initialized.
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call validate_auth() first.")

        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

        progress_file = get_progress_file(pdf_path, output_dir)
        output_file = get_output_file(pdf_path, output_dir)
        log_file = get_log_file(pdf_path, output_dir)

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
                    f"[yellow]Resuming from previous session. "
                    f"{len(state.completed_pages)} pages already done.[/yellow]"
                )

        if not state:
            state = ProgressState(
                pdf_path=str(pdf_path), total_pages=max(pages) if pages else 0
            )

        pending_pages = state.get_pending_pages(pages)

        if dry_run:
            console.print(f"\n[bold]Dry Run - Would process:[/bold]")
            console.print(f"  PDF: {pdf_path}")
            console.print(f"  Total pages requested: {len(pages)}")
            console.print(f"  Already completed: {len(state.completed_pages)}")
            console.print(f"  Pending: {len(pending_pages)}")
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All requested pages already processed![/green]")
            return len(state.completed_pages), len(state.failed_pages), output_file

        console.print(f"\n[bold]Processing {len(pending_pages)} pages...[/bold]")
        console.print(f"  Log file: {log_file}")

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

                    result = self._process_single_page(images[0], page_num)

                    if result.success:
                        results[page_num] = result.text
                        state.mark_completed(page_num)
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
                    console.print("[green]Progress saved. Resume with: --resume[/green]")
                    raise

                except Exception as exc:
                    logger.error("Page %d: Unexpected error - %s", page_num, exc)
                    state.mark_failed(page_num)
                    state.save(progress_file)
                    progress.advance(task)

        write_markdown_output(pdf_path, results, output_file)

        total_time = time.time() - start_time
        logger.info(
            "Processing complete. Success: %d, Failed: %d, Time: %s",
            len(state.completed_pages),
            len(state.failed_pages),
            format_duration(total_time),
        )

        return len(state.completed_pages), len(state.failed_pages), output_file
