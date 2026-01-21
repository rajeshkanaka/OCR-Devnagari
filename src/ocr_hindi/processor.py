"""
Core OCR processing logic using Gemini + Vertex AI
"""

import logging
import os
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
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
)

# Load environment variables from .env file (fallback for GEMINI_API_KEY)
load_dotenv()

console = Console()
logger = logging.getLogger(__name__)


@dataclass
class ProcessingResult:
    """Result of processing a single page"""

    page_num: int
    text: str
    success: bool
    error: Optional[str] = None
    duration: float = 0.0


@dataclass
class OCRConfig:
    """Configuration for OCR processing"""

    model: str = "gemini-3-flash-preview"
    dpi: int = 200
    rate_limit: int = 15  # requests per minute
    max_retries: int = 3
    retry_base_delay: float = 2.0  # exponential backoff base


class OCRProcessor:
    """Handles OCR processing of PDF files using Gemini"""

    def __init__(self, config: Optional[OCRConfig] = None):
        self.config = config or OCRConfig()
        self.client = None
        self._last_request_time = 0.0
        self._min_request_interval = 60.0 / self.config.rate_limit

    def validate_auth(self) -> tuple[bool, str, str]:
        """
        Validate authentication and return status.

        Returns:
            Tuple of (success, auth_method, message)
        """
        try:
            from google import genai

            # Check for Vertex AI environment variables
            use_vertex = os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in (
                "1",
                "true",
                "yes",
            )
            project = os.getenv("GOOGLE_CLOUD_PROJECT")
            location = os.getenv("GOOGLE_CLOUD_LOCATION", "global")

            if use_vertex and project:
                # Try Vertex AI
                self.client = genai.Client(
                    vertexai=True, project=project, location=location
                )
                # Test with a simple request
                response = self.client.models.generate_content(
                    model=self.config.model, contents="Say 'OK'"
                )
                if response.text:
                    return (
                        True,
                        "Vertex AI",
                        f"Project: {project}, Location: {location}",
                    )

            # Try Gemini API key
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
                "No valid authentication found. Set GOOGLE_GENAI_USE_VERTEXAI=1 with GOOGLE_CLOUD_PROJECT, or set GEMINI_API_KEY",
            )

        except Exception as e:
            return False, "Error", f"Authentication failed: {str(e)}"

    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.time()

    def _process_single_page(
        self, image: Image.Image, page_num: int
    ) -> ProcessingResult:
        """Process a single page image with retries"""
        from google import genai
        from google.genai import types

        start_time = time.time()

        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()

                # Send image with OCR prompt
                response = self.client.models.generate_content(
                    model=self.config.model, contents=[image, OCR_PROMPT]
                )

                text = response.text.strip() if response.text else ""
                duration = time.time() - start_time

                logger.info(f"Page {page_num}: Extracted {len(text)} characters")

                return ProcessingResult(
                    page_num=page_num, text=text, success=True, duration=duration
                )

            except Exception as e:
                error_msg = str(e)
                logger.warning(
                    f"Page {page_num}, attempt {attempt + 1}/{self.config.max_retries}: {error_msg}"
                )

                if "429" in error_msg or "quota" in error_msg.lower():
                    # Rate limit error - wait longer
                    delay = self.config.retry_base_delay * (2**attempt) * 2
                    logger.info(f"Rate limited. Waiting {delay}s before retry...")
                    time.sleep(delay)
                elif attempt < self.config.max_retries - 1:
                    # Other error - standard backoff
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
    ) -> tuple[int, int, Path]:
        """
        Process specified pages from a PDF file.

        Args:
            pdf_path: Path to the PDF file
            pages: List of page numbers to process (1-indexed)
            resume: Whether to resume from previous progress
            dry_run: If True, only show what would be processed

        Returns:
            Tuple of (successful_count, failed_count, output_path)
        """
        if not self.client:
            raise RuntimeError("Client not initialized. Call validate_auth() first.")

        progress_file = get_progress_file(pdf_path)
        output_file = get_output_file(pdf_path)
        log_file = get_log_file(pdf_path)

        # Setup file logging
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
                    f"[yellow]Resuming from previous session. {len(state.completed_pages)} pages already done.[/yellow]"
                )

        if not state:
            state = ProgressState(
                pdf_path=str(pdf_path), total_pages=max(pages) if pages else 0
            )

        # Get pending pages
        pending_pages = state.get_pending_pages(pages)

        if dry_run:
            console.print(f"\n[bold]Dry Run - Would process:[/bold]")
            console.print(f"  PDF: {pdf_path}")
            console.print(f"  Total pages requested: {len(pages)}")
            console.print(f"  Already completed: {len(state.completed_pages)}")
            console.print(f"  Pending: {len(pending_pages)}")
            console.print(
                f"  Pages: {pending_pages[:10]}{'...' if len(pending_pages) > 10 else ''}"
            )
            return 0, 0, output_file

        if not pending_pages:
            console.print("[green]All requested pages already processed![/green]")
            return len(state.completed_pages), len(state.failed_pages), output_file

        console.print(f"\n[bold]Processing {len(pending_pages)} pages...[/bold]")
        console.print(f"  Log file: {log_file}")

        # Results storage
        results: dict[int, str] = {}

        # Load existing results if resuming
        if output_file.exists() and resume:
            # Parse existing output to get completed pages
            pass  # Results will be appended

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

            for i, page_num in enumerate(pending_pages):
                try:
                    progress.update(task, description=f"Page {page_num}")

                    # Convert single page to image
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

                    # Process the page
                    result = self._process_single_page(images[0], page_num)

                    if result.success:
                        results[page_num] = result.text
                        state.mark_completed(page_num)
                    else:
                        state.mark_failed(page_num)
                        logger.error(f"Page {page_num}: {result.error}")

                    # Save progress after each page
                    state.save(progress_file)
                    progress.advance(task)

                except KeyboardInterrupt:
                    console.print("\n[yellow]Interrupted! Saving progress...[/yellow]")
                    state.save(progress_file)
                    console.print(
                        f"[green]Progress saved. Resume with: --resume[/green]"
                    )
                    raise

                except Exception as e:
                    logger.error(f"Page {page_num}: Unexpected error - {str(e)}")
                    state.mark_failed(page_num)
                    state.save(progress_file)
                    progress.advance(task)

        # Write output file
        self._write_output(pdf_path, results, output_file, pages)

        total_time = time.time() - start_time
        logger.info(
            f"Processing complete. Success: {len(state.completed_pages)}, Failed: {len(state.failed_pages)}, Time: {format_duration(total_time)}"
        )

        return len(state.completed_pages), len(state.failed_pages), output_file

    def _write_output(
        self,
        pdf_path: Path,
        results: dict[int, str],
        output_file: Path,
        pages: list[int],
    ) -> None:
        """Write OCR results to markdown file"""
        # If file exists, read existing content to merge
        existing_results: dict[int, str] = {}
        if output_file.exists():
            # Parse existing file to extract page contents
            content = output_file.read_text(encoding="utf-8")
            # Simple parsing - could be improved
            import re

            for match in re.finditer(
                r"## Page (\d+)\n\n(.*?)(?=\n---|\Z)", content, re.DOTALL
            ):
                page_num = int(match.group(1))
                text = match.group(2).strip()
                existing_results[page_num] = text

        # Merge results
        all_results = {**existing_results, **results}

        # Generate output
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
