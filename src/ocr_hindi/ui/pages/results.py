"""Screen 4 — Results Viewer.

Side-by-side: rendered PDF page on the left, extracted text on the right.
Reads from `OCRCache.get(N)` and uses pdf2image for the rendered image.
"""

from __future__ import annotations

import io
import json
from pathlib import Path

import streamlit as st

from ocr_hindi.backends.mantra_detector import MantraDetector
from ocr_hindi.cache import OCRCache
from ocr_hindi.ui import components
from ocr_hindi.ui.layout import setup_page, sidebar_footer
from ocr_hindi.utils import ProgressState, get_progress_file


def _render_page_image(pdf_path: Path, page_num: int, dpi: int = 150) -> bytes | None:
    """Render a single PDF page to PNG bytes using pdf2image."""
    try:
        from pdf2image import convert_from_path
    except ImportError:
        return None
    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=page_num,
            last_page=page_num,
            fmt="png",
        )
    except Exception:  # noqa: BLE001
        return None
    if not images:
        return None
    buf = io.BytesIO()
    images[0].save(buf, format="PNG")
    return buf.getvalue()


def _meta_for(cache: OCRCache, page: int) -> dict[str, object]:
    """Read a page's metadata, returning {} if missing/corrupt."""
    meta_file = cache.cache_dir / f"page_{page:04d}.meta.json"
    if not meta_file.exists():
        return {}
    try:
        return json.loads(meta_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def render() -> None:
    setup_page("Results")

    pdf_path: Path | None = st.session_state.get("last_pdf")
    output_dir: Path | None = st.session_state.get("last_output_dir")

    components.page_header(
        crumbs=["Workflow", "Results", pdf_path.stem if pdf_path else "—"],
        title=pdf_path.stem if pdf_path else "No completed job yet",
        sub=(
            "Review the rendered page next to the extracted Devanagari text. "
            "Edits write back to the on-disk cache."
            if pdf_path
            else "Process a PDF first, then return here to review the output."
        ),
    )

    if not pdf_path or not output_dir:
        st.info("Nothing to show. Configure and run a job in **Configure & Run**.")
        sidebar_footer()
        return

    cache = OCRCache(pdf_path, output_dir)
    state_obj = ProgressState.load(get_progress_file(pdf_path, output_dir))
    cached_pages = cache.pages()
    total = state_obj.total_pages if state_obj else (cached_pages[-1] if cached_pages else 0)

    if not cached_pages:
        st.warning("No pages have been cached yet — try the Live Processing screen.")
        sidebar_footer()
        return

    # Page navigation strip
    components.card_open("Navigate", f"{len(cached_pages)} of {total} pages cached")
    nav_l, nav_m, nav_r = st.columns([1, 2, 2])
    with nav_l:
        page = st.number_input(
            "Page",
            min_value=cached_pages[0],
            max_value=cached_pages[-1],
            value=int(st.session_state.get("current_page", cached_pages[0])),
            step=1,
            key="current_page",
            label_visibility="collapsed",
        )
    with nav_m:
        b1, b2, b3 = st.columns(3)
        with b1:
            if st.button("◀ Prev", use_container_width=True):
                idx = max(0, cached_pages.index(page) - 1) if page in cached_pages else 0
                st.session_state["current_page"] = cached_pages[idx]
                st.rerun()
        with b2:
            if st.button("Next ▶", use_container_width=True):
                idx = (
                    min(len(cached_pages) - 1, cached_pages.index(page) + 1)
                    if page in cached_pages
                    else 0
                )
                st.session_state["current_page"] = cached_pages[idx]
                st.rerun()
        with b3:
            if st.button("First mantra", use_container_width=True):
                detector = MantraDetector()
                for p in cached_pages:
                    text = cache.get(p) or ""
                    if detector.detect(text).contains_mantra:
                        st.session_state["current_page"] = p
                        st.rerun()
    with nav_r:
        st.caption(f"Pages cached: {cached_pages[:6]}{' …' if len(cached_pages) > 6 else ''}")
    components.card_close()

    # Side by side
    text = cache.get(page) or ""
    meta = _meta_for(cache, page)
    backend_used = str(meta.get("backend_used", ""))
    confidence = float(meta.get("confidence", 0) or 0)

    detector = MantraDetector()
    mantra_result = detector.detect(text)

    img_col, text_col = st.columns(2)

    with img_col:
        components.card_open(f"Page {page} · scan", "rendered with pdf2image at 150 dpi")
        png = _render_page_image(pdf_path, page)
        if png is not None:
            st.image(png, use_container_width=True)
        else:
            st.info("Couldn't render this page. Check that pdf2image and poppler are installed.")
        components.card_close()

    with text_col:
        badge_kind = "saffron" if "gemini" in backend_used.lower() else "sage"
        components.card_open(
            "Extracted text",
            f"{components.badge(backend_used.upper() or 'OCR', badge_kind)} "
            f"<span class='mono'>conf {confidence:.2f} · {len(text)} chars</span>",
        )
        if mantra_result.contains_mantra:
            components.mantra_alert(
                f"Mantra detected on this page · {mantra_result.mantra_count} marker(s) · "
                f"recommendation: {mantra_result.recommendation}."
            )
        if text.strip():
            components.deva_block(text)
        else:
            st.warning("This page is cached but the text body is empty.")
        st.caption(
            f"{cache.cache_dir.name}/page_{page:04d}.txt · saved {meta.get('timestamp', '—')}"
        )
        components.card_close()

    sidebar_footer()


if __name__ == "__main__":
    render()
