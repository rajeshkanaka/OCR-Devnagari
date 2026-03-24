"""Utility functions for OCR processing."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class ProgressState:
    """Tracks OCR processing progress for resume capability."""

    pdf_path: str
    total_pages: int
    completed_pages: list[int] = field(default_factory=list)
    failed_pages: list[int] = field(default_factory=list)
    started_at: str = ""
    last_updated: str = ""

    def __post_init__(self) -> None:
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()

    @classmethod
    def load(cls, progress_file: Path) -> ProgressState | None:
        """Load progress from a JSON file.

        Args:
            progress_file: Path to the progress JSON file.

        Returns:
            Loaded state, or None if file missing or corrupt.
        """
        if not progress_file.exists():
            return None
        try:
            data = json.loads(progress_file.read_text(encoding="utf-8"))
            return cls(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def save(self, progress_file: Path) -> None:
        """Save progress to a JSON file.

        Args:
            progress_file: Path to write the progress JSON.
        """
        self.last_updated = datetime.now().isoformat()
        progress_file.write_text(
            json.dumps(
                {
                    "pdf_path": self.pdf_path,
                    "total_pages": self.total_pages,
                    "completed_pages": self.completed_pages,
                    "failed_pages": self.failed_pages,
                    "started_at": self.started_at,
                    "last_updated": self.last_updated,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def mark_completed(self, page: int) -> None:
        """Mark a page as successfully completed.

        Args:
            page: 1-indexed page number.
        """
        if page not in self.completed_pages:
            self.completed_pages.append(page)
        if page in self.failed_pages:
            self.failed_pages.remove(page)

    def mark_failed(self, page: int) -> None:
        """Mark a page as failed.

        Args:
            page: 1-indexed page number.
        """
        if page not in self.failed_pages:
            self.failed_pages.append(page)

    def get_pending_pages(self, requested_pages: list[int]) -> list[int]:
        """Get pages that still need processing.

        Args:
            requested_pages: Full list of requested page numbers.

        Returns:
            Pages not yet in completed_pages.
        """
        return [p for p in requested_pages if p not in self.completed_pages]


def parse_page_range(page_spec: str, max_pages: int) -> list[int]:
    """Parse page range specification like print dialogs.

    Examples:
        "all" -> [1, 2, 3, ..., max_pages]
        "5" -> [5]
        "1-50" -> [1, 2, ..., 50]
        "1,5,10-20,30" -> [1, 5, 10, 11, ..., 20, 30]

    Args:
        page_spec: Page specification string.
        max_pages: Maximum number of pages in the PDF.

    Returns:
        Sorted list of unique page numbers (1-indexed).

    Raises:
        ValueError: If page specification is invalid.
    """
    page_spec = page_spec.strip().lower()

    if page_spec == "all":
        return list(range(1, max_pages + 1))

    pages: set[int] = set()
    parts = [p.strip() for p in page_spec.split(",")]

    for part in parts:
        if not part:
            continue

        if "-" in part:
            match = re.match(r"^(\d+)\s*-\s*(\d+)$", part)
            if not match:
                raise ValueError(f"Invalid range format: '{part}'")

            start, end = int(match.group(1)), int(match.group(2))

            if start > end:
                raise ValueError(f"Invalid range: start ({start}) > end ({end})")
            if start < 1:
                raise ValueError(f"Page numbers must be >= 1, got {start}")
            if end > max_pages:
                raise ValueError(
                    f"Page {end} exceeds PDF length ({max_pages} pages)"
                )

            pages.update(range(start, end + 1))
        else:
            if not part.isdigit():
                raise ValueError(f"Invalid page number: '{part}'")

            page = int(part)
            if page < 1:
                raise ValueError(f"Page numbers must be >= 1, got {page}")
            if page > max_pages:
                raise ValueError(
                    f"Page {page} exceeds PDF length ({max_pages} pages)"
                )

            pages.add(page)

    if not pages:
        raise ValueError("No pages specified")

    return sorted(pages)


def get_progress_file(pdf_path: Path, output_dir: Path | None = None) -> Path:
    """Get the progress file path for a given PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: If provided, place the progress file here.
    """
    parent = output_dir if output_dir else pdf_path.parent
    return parent / f".ocr_progress_{pdf_path.stem}.json"


def get_output_file(pdf_path: Path, output_dir: Path | None = None) -> Path:
    """Get the output markdown file path for a given PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: If provided, place the output file here.
    """
    parent = output_dir if output_dir else pdf_path.parent
    return parent / f"{pdf_path.stem}_unicode.md"


def get_log_file(pdf_path: Path, output_dir: Path | None = None) -> Path:
    """Get the log file path for a given PDF.

    Args:
        pdf_path: Path to the PDF file.
        output_dir: If provided, place the log file here.
    """
    parent = output_dir if output_dir else pdf_path.parent
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return parent / f"ocr_{pdf_path.stem}_{timestamp}.log"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format.

    Args:
        seconds: Duration in seconds.

    Returns:
        Formatted string like "1m 30s" or "2h 15m 0s".
    """
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hours}h {minutes}m {secs}s"


def estimate_processing_time(num_pages: int, rate_limit: int = 15) -> str:
    """Estimate processing time based on rate limit.

    Args:
        num_pages: Number of pages to process.
        rate_limit: Requests per minute.

    Returns:
        Human-readable time estimate.
    """
    seconds_per_page = 60.0 / rate_limit + 1  # +1s for processing overhead
    total_seconds = num_pages * seconds_per_page
    return format_duration(total_seconds)


def write_markdown_output(
    pdf_path: Path,
    results: dict[int, str],
    output_file: Path,
    *,
    backend_name: str = "",
) -> None:
    """Write OCR results to a markdown file, merging with existing content.

    Args:
        pdf_path: Path to the source PDF (used for the title).
        results: Mapping of page numbers to OCR text.
        output_file: Path to the output markdown file.
        backend_name: Optional backend name to include in the header.
    """
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
        if backend_name:
            f.write(f"Backend: {backend_name}\n")
        f.write(f"Pages processed: {len(sorted_pages)}\n\n")
        f.write("---\n\n")

        for page_num in sorted_pages:
            f.write(f"## Page {page_num}\n\n")
            f.write(all_results[page_num])
            f.write("\n\n---\n\n")
