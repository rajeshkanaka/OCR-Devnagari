"""
Crash-safe file-based cache for OCR results.

Each page is stored as a separate file with atomic writes to ensure
no data loss on crashes. This enables:
1. Crash recovery - only current page lost
2. Resume capability - skip already cached pages
3. Memory efficiency - don't hold all results in RAM
"""

import json
import logging
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class CachedPage:
    """Metadata for a cached page."""

    page_num: int
    text: str
    backend_used: str = ""
    confidence: float = 1.0
    timestamp: str = ""


class OCRCache:
    """
    File-based cache for OCR results.

    Each page = one file = atomic write = crash-safe.

    Cache structure:
        .ocr_cache_{pdf_stem}/
            page_0001.txt       # Raw text content
            page_0002.txt
            ...
            metadata.json       # Optional metadata for tracking

    Usage:
        cache = OCRCache(pdf_path)

        # Save a page (atomic write)
        cache.save(page_num=1, text="...", backend="hybrid")

        # Check if cached
        if cache.has(1):
            text = cache.get(1)

        # Get all cached pages
        results = cache.all_results()

        # Cleanup after successful completion
        cache.cleanup()
    """

    def __init__(self, pdf_path: Path):
        """
        Initialize cache for a PDF file.

        Args:
            pdf_path: Path to the PDF file being processed.
                      Cache directory will be created alongside it.
        """
        self.pdf_path = Path(pdf_path)
        self.cache_dir = self.pdf_path.parent / f".ocr_cache_{self.pdf_path.stem}"
        self._ensure_cache_dir()

    def _ensure_cache_dir(self) -> None:
        """Create cache directory if it doesn't exist."""
        self.cache_dir.mkdir(exist_ok=True)

    def _page_path(self, page: int) -> Path:
        """Get the file path for a page's cached text."""
        return self.cache_dir / f"page_{page:04d}.txt"

    def _meta_path(self, page: int) -> Path:
        """Get the file path for a page's metadata."""
        return self.cache_dir / f"page_{page:04d}.meta.json"

    def save(
        self,
        page_num: int,
        text: str,
        backend: str = "",
        confidence: float = 1.0,
    ) -> None:
        """
        Save a page's OCR result atomically.

        Uses atomic write pattern: write to temp file, then rename.
        This ensures we never have a partial write on crash.

        Args:
            page_num: Page number (1-indexed)
            text: OCR text content
            backend: Backend used for OCR (e.g., "hybrid:easyocr+gemini")
            confidence: Confidence score (0.0-1.0)
        """
        target = self._page_path(page_num)
        temp = target.with_suffix(".tmp")

        try:
            # Write text to temp file
            temp.write_text(text, encoding="utf-8")

            # Atomic rename (POSIX guarantees atomicity)
            temp.rename(target)

            # Save metadata (non-critical, can fail)
            try:
                from datetime import datetime

                meta = CachedPage(
                    page_num=page_num,
                    text="",  # Don't duplicate text in meta
                    backend_used=backend,
                    confidence=confidence,
                    timestamp=datetime.now().isoformat(),
                )
                meta_path = self._meta_path(page_num)
                meta_path.write_text(
                    json.dumps(asdict(meta), ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )
            except Exception as e:
                logger.debug(f"Failed to save metadata for page {page_num}: {e}")

            logger.debug(f"Cached page {page_num}: {len(text)} chars")

        except Exception as e:
            logger.error(f"Failed to cache page {page_num}: {e}")
            # Clean up temp file if it exists
            if temp.exists():
                try:
                    temp.unlink()
                except Exception:
                    pass
            raise

    def get(self, page: int) -> Optional[str]:
        """
        Get cached text for a page.

        Args:
            page: Page number (1-indexed)

        Returns:
            Cached text or None if not cached.
        """
        path = self._page_path(page)
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Failed to read cache for page {page}: {e}")
        return None

    def has(self, page: int) -> bool:
        """
        Check if a page is cached.

        Args:
            page: Page number (1-indexed)

        Returns:
            True if page is cached.
        """
        return self._page_path(page).exists()

    def pages(self) -> list[int]:
        """
        List all cached page numbers.

        Returns:
            Sorted list of cached page numbers.
        """
        cached = []
        for f in self.cache_dir.glob("page_*.txt"):
            try:
                # Extract page number from "page_0001.txt"
                page_num = int(f.stem.split("_")[1])
                cached.append(page_num)
            except (ValueError, IndexError):
                continue
        return sorted(cached)

    def all_results(self) -> dict[int, str]:
        """
        Load all cached results.

        Returns:
            Dict mapping page numbers to their text content.
        """
        results = {}
        for page in self.pages():
            text = self.get(page)
            if text is not None:
                results[page] = text
        return results

    def count(self) -> int:
        """
        Get count of cached pages.

        Returns:
            Number of cached pages.
        """
        return len(list(self.cache_dir.glob("page_*.txt")))

    def get_pending_pages(self, requested_pages: list[int]) -> list[int]:
        """
        Get pages that still need processing.

        Args:
            requested_pages: List of pages requested for processing.

        Returns:
            List of pages not yet cached.
        """
        cached = set(self.pages())
        return [p for p in requested_pages if p not in cached]

    def cleanup(self, keep_on_success: bool = False) -> None:
        """
        Remove cache directory.

        Call this after successful completion if you don't need the cache.

        Args:
            keep_on_success: If True, don't delete (useful for debugging).
        """
        if keep_on_success:
            logger.info(f"Keeping cache at {self.cache_dir}")
            return

        try:
            # Remove all files in cache dir
            for f in self.cache_dir.iterdir():
                try:
                    f.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete {f}: {e}")

            # Remove the directory itself
            self.cache_dir.rmdir()
            logger.debug(f"Cleaned up cache: {self.cache_dir}")

        except Exception as e:
            logger.warning(f"Failed to cleanup cache: {e}")

    def get_cache_size_mb(self) -> float:
        """
        Get total cache size in MB.

        Returns:
            Cache size in megabytes.
        """
        total_bytes = sum(
            f.stat().st_size for f in self.cache_dir.iterdir() if f.is_file()
        )
        return total_bytes / (1024 * 1024)

    def __repr__(self) -> str:
        return f"OCRCache(pdf={self.pdf_path.name}, cached={self.count()} pages)"
