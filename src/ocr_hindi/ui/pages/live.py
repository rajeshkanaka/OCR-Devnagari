"""Screen 3 — Live Processing dashboard.

Polls `OCRCache` and `ProgressState` for the most recent job and
renders a stat row, the page atlas, the worker table and a tailing
log stream.
"""

from __future__ import annotations

import json
import time
from datetime import datetime
from pathlib import Path

import streamlit as st

from ocr_hindi.cache import OCRCache
from ocr_hindi.ui import components, state
from ocr_hindi.ui.layout import setup_page, sidebar_footer
from ocr_hindi.utils import ProgressState, get_log_file, get_progress_file


def _latest_log_file(pdf_path: Path, output_dir: Path) -> Path | None:
    """Return the most recent log file for this PDF, if any."""
    pattern = f"ocr_{pdf_path.stem}_*.log"
    candidates = sorted(output_dir.glob(pattern))
    return candidates[-1] if candidates else None


def _read_log_tail(log_path: Path, limit: int = 80) -> list[tuple[str, str, str]]:
    """Read the last `limit` log lines and split them into (ts, lvl, msg)."""
    if not log_path.exists():
        return []
    try:
        raw = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return []
    out: list[tuple[str, str, str]] = []
    for line in raw[-limit:]:
        parts = line.split(" - ", 2)
        if len(parts) == 3:
            out.append((parts[0][11:23], parts[1], parts[2]))
        else:
            out.append(("", "INFO", line))
    return out


def _atlas(state_obj: ProgressState, cache: OCRCache, total: int) -> list[str]:
    """Build the per-page status grid for the atlas."""
    cache_pages = set(cache.pages())
    failed = set(state_obj.failed_pages)
    cells: list[str] = []
    cache_dir = cache.cache_dir
    for page in range(1, total + 1):
        if page in failed:
            cells.append("failed")
            continue
        if page in cache_pages:
            meta_file = cache_dir / f"page_{page:04d}.meta.json"
            backend = ""
            if meta_file.exists():
                try:
                    backend = json.loads(meta_file.read_text(encoding="utf-8")).get(
                        "backend_used", ""
                    )
                except (json.JSONDecodeError, OSError):
                    backend = ""
            cells.append("gemini" if "gemini" in backend.lower() else "easyocr")
        else:
            cells.append("pending")
    return cells


def render() -> None:
    setup_page("Live Processing")

    pdf_path: Path | None = st.session_state.get("last_pdf")
    output_dir: Path | None = st.session_state.get("last_output_dir")

    components.page_header(
        crumbs=["Workflow", "Live Processing"],
        title=pdf_path.stem if pdf_path else "No active job",
        sub=(
            "Progress polled from the on-disk cache · auto-refresh every 2 seconds."
            if pdf_path
            else "Start a job from Configure & Run to populate this dashboard."
        ),
    )

    if not pdf_path or not output_dir:
        st.info("Nothing running yet. Configure a job in **Configure & Run**.")
        sidebar_footer()
        return

    progress_file = get_progress_file(pdf_path, output_dir)
    state_obj = ProgressState.load(progress_file)
    cache = OCRCache(pdf_path, output_dir)
    total = state_obj.total_pages if state_obj else int(st.session_state.get("uploaded_pages") or 0)
    done = len(state_obj.completed_pages) if state_obj else cache.count()
    failed = len(state_obj.failed_pages) if state_obj else 0

    pct = (done / total * 100) if total else 0
    cache_size = cache.get_cache_size_mb()

    # Top stat row
    s1, s2, s3, s4 = st.columns([2, 1, 1, 1])
    with s1:
        components.stat_tile("Progress", f"{done} / {total}", delta=f"{pct:.1f}% complete")
        st.progress(min(pct / 100.0, 1.0))
    with s2:
        components.stat_tile(
            "Cost so far",
            "—" if not pdf_path else "$0.00",
            delta="updated as cache fills",
        )
    with s3:
        # Mantra count: scan meta files (cheap because pages are bounded by completed)
        mantra_count = 0
        for page in cache.pages():
            meta = cache.cache_dir / f"page_{page:04d}.meta.json"
            if meta.exists():
                try:
                    if "mantra" in meta.read_text(encoding="utf-8").lower():
                        mantra_count += 1
                except OSError:
                    continue
        components.stat_tile("Mantras detected", str(mantra_count), delta="from page metadata")
    with s4:
        components.stat_tile(
            "Cache size",
            f"{cache_size:.1f} MB",
            delta=f"{done} .txt files written",
        )

    st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)

    # Atlas + log columns
    grid_col, side_col = st.columns([1.4, 1])

    with grid_col:
        components.card_open("Page atlas", "color = engine that handled it")
        if state_obj and total:
            cells = _atlas(state_obj, cache, total)
            components.atlas_grid(cells)
            st.markdown(
                f'<div class="mono" style="display:flex;justify-content:space-between;'
                f'margin-top:14px;font-size:11px;color:var(--ink-500);">'
                f"<span>{done - failed} cached · {failed} failed</span>"
                f"<span>{total - done} pending</span></div>",
                unsafe_allow_html=True,
            )
        else:
            st.info("Atlas will appear after the first page completes.")
        components.card_close()

    with side_col:
        components.card_open(
            "Workers",
            f"{st.session_state.get('workers', 5)} concurrent · 60 RPM rate limit",
        )
        # Inferred per-page activity: take the most-recent N completed pages.
        recent = sorted(state_obj.completed_pages)[-8:] if state_obj else []
        if recent:
            for page in recent:
                meta_file = cache.cache_dir / f"page_{page:04d}.meta.json"
                backend = ""
                if meta_file.exists():
                    try:
                        backend = json.loads(meta_file.read_text(encoding="utf-8")).get(
                            "backend_used", ""
                        )
                    except (json.JSONDecodeError, OSError):
                        backend = ""
                colour = "var(--saffron-700)" if "gemini" in backend.lower() else "var(--sage-600)"
                st.markdown(
                    f'<div style="display:flex;gap:10px;padding:5px 0;font-size:11.5px;'
                    f'border-bottom:1px dashed var(--surface-alt);">'
                    f'<span class="mono" style="width:50px;color:var(--ink-700);">p.{page}</span>'
                    f'<span style="flex:1;color:{colour};font-family:var(--font-mono);font-size:10px;">{backend or "ocr"}</span>'
                    f'<span class="mono" style="color:var(--ink-400);font-size:10px;">cached</span>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
        else:
            st.write("Waiting for the first page…")
        components.card_close()

        components.card_open("Log stream", f"tail -f {pdf_path.stem}.log")
        log_path = _latest_log_file(pdf_path, output_dir)
        if log_path:
            components.log_stream(_read_log_tail(log_path, limit=40))
        else:
            st.info(f"Log file will appear at {get_log_file(pdf_path, output_dir).name}")
        components.card_close()

    # Auto-refresh
    if st.session_state.get("live_running") and (state_obj is None or done < total):
        time.sleep(2)
        st.rerun()
    elif state_obj and done >= total and total > 0:
        st.success(f"Job complete · {done} pages cached at {output_dir}")
    sidebar_footer()


if __name__ == "__main__":
    render()
