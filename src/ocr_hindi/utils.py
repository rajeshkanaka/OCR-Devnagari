"""
Utility functions for OCR processing
"""

import json
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ProgressState:
    """Tracks OCR processing progress for resume capability"""

    pdf_path: str
    total_pages: int
    completed_pages: list[int] = field(default_factory=list)
    failed_pages: list[int] = field(default_factory=list)
    started_at: str = ""
    last_updated: str = ""

    def __post_init__(self):
        if not self.started_at:
            self.started_at = datetime.now().isoformat()
        self.last_updated = datetime.now().isoformat()

    @classmethod
    def load(cls, progress_file: Path) -> Optional["ProgressState"]:
        """Load progress from file"""
        if not progress_file.exists():
            return None
        try:
            with open(progress_file, "r") as f:
                data = json.load(f)
            return cls(**data)
        except (json.JSONDecodeError, TypeError, KeyError):
            return None

    def save(self, progress_file: Path) -> None:
        """Save progress to file"""
        self.last_updated = datetime.now().isoformat()
        with open(progress_file, "w") as f:
            json.dump(
                {
                    "pdf_path": self.pdf_path,
                    "total_pages": self.total_pages,
                    "completed_pages": self.completed_pages,
                    "failed_pages": self.failed_pages,
                    "started_at": self.started_at,
                    "last_updated": self.last_updated,
                },
                f,
                indent=2,
            )

    def mark_completed(self, page: int) -> None:
        """Mark a page as completed"""
        if page not in self.completed_pages:
            self.completed_pages.append(page)
        if page in self.failed_pages:
            self.failed_pages.remove(page)

    def mark_failed(self, page: int) -> None:
        """Mark a page as failed"""
        if page not in self.failed_pages:
            self.failed_pages.append(page)

    def get_pending_pages(self, requested_pages: list[int]) -> list[int]:
        """Get pages that still need processing"""
        return [p for p in requested_pages if p not in self.completed_pages]


def parse_page_range(page_spec: str, max_pages: int) -> list[int]:
    """
    Parse page range specification like print dialogs.

    Examples:
        "all" -> [1, 2, 3, ..., max_pages]
        "5" -> [5]
        "1-50" -> [1, 2, ..., 50]
        "1,5,10-20,30" -> [1, 5, 10, 11, ..., 20, 30]

    Args:
        page_spec: Page specification string
        max_pages: Maximum number of pages in the PDF

    Returns:
        Sorted list of unique page numbers (1-indexed)

    Raises:
        ValueError: If page specification is invalid
    """
    page_spec = page_spec.strip().lower()

    if page_spec == "all":
        return list(range(1, max_pages + 1))

    pages: set[int] = set()

    # Split by comma
    parts = [p.strip() for p in page_spec.split(",")]

    for part in parts:
        if not part:
            continue

        # Check for range (e.g., "1-50")
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
                raise ValueError(f"Page {end} exceeds PDF length ({max_pages} pages)")

            pages.update(range(start, end + 1))
        else:
            # Single page
            if not part.isdigit():
                raise ValueError(f"Invalid page number: '{part}'")

            page = int(part)
            if page < 1:
                raise ValueError(f"Page numbers must be >= 1, got {page}")
            if page > max_pages:
                raise ValueError(f"Page {page} exceeds PDF length ({max_pages} pages)")

            pages.add(page)

    if not pages:
        raise ValueError("No pages specified")

    return sorted(pages)


def get_progress_file(pdf_path: Path) -> Path:
    """Get the progress file path for a given PDF"""
    return pdf_path.parent / f".ocr_progress_{pdf_path.stem}.json"


def get_output_file(pdf_path: Path) -> Path:
    """Get the output markdown file path for a given PDF"""
    return pdf_path.parent / f"{pdf_path.stem}_unicode.md"


def get_log_file(pdf_path: Path) -> Path:
    """Get the log file path for a given PDF"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return pdf_path.parent / f"ocr_{pdf_path.stem}_{timestamp}.log"


def format_duration(seconds: float) -> str:
    """Format duration in human-readable format"""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes}m {secs}s"
    else:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hours}h {minutes}m {secs}s"


def estimate_processing_time(num_pages: int, rate_limit: int = 15) -> str:
    """
    Estimate processing time based on rate limit.

    Args:
        num_pages: Number of pages to process
        rate_limit: Requests per minute

    Returns:
        Human-readable time estimate
    """
    # Each page = 1 request, plus some overhead
    seconds_per_page = 60.0 / rate_limit + 1  # +1s for processing overhead
    total_seconds = num_pages * seconds_per_page
    return format_duration(total_seconds)
