"""Screen 1 — Configure & Run.

Maps every CLI flag of `ocr-hindi ocr` to a Streamlit control and
hands off to `MultiBackendProcessor.process_pdf_async` when the user
clicks **Begin processing**.
"""

from __future__ import annotations

import asyncio
import tempfile
import threading
from pathlib import Path

import streamlit as st

from ocr_hindi.multi_processor import MultiBackendProcessor, MultiProcessorConfig
from ocr_hindi.ui import components, engines, state
from ocr_hindi.ui.layout import setup_page, sidebar_footer
from ocr_hindi.utils import format_duration, parse_page_range


def _save_uploaded(file) -> Path:
    """Persist an uploaded PDF to a temp file and return the path."""
    tmp_dir = Path(tempfile.gettempdir()) / "ocr_uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    path = tmp_dir / file.name
    with open(path, "wb") as out:
        out.write(file.getbuffer())
    return path


def _detect_pages(path: Path) -> int:
    """Return total pages in the PDF, or 0 if pdfinfo fails."""
    try:
        from pdf2image import pdfinfo_from_path

        return int(pdfinfo_from_path(str(path))["Pages"])
    except Exception:  # noqa: BLE001 - UI is degraded, not crashed
        return 0


def _start_job(
    pdf_path: Path, page_list: list[int], cfg: MultiProcessorConfig, output_dir: Path, resume: bool
) -> None:
    """Spawn a background thread that runs the async OCR processor."""

    def runner() -> None:
        processor = MultiBackendProcessor(config=cfg)
        ok, _, msg = processor.initialize(quiet=True)
        if not ok:
            st.session_state["last_error"] = msg
            st.session_state["live_running"] = False
            return
        try:
            asyncio.run(
                processor.process_pdf_async(
                    pdf_path,
                    page_list,
                    resume=resume,
                    dry_run=False,
                    output_dir=output_dir,
                )
            )
        except Exception as exc:  # noqa: BLE001
            st.session_state["last_error"] = str(exc)
        finally:
            processor.cleanup()
            st.session_state["live_running"] = False

    thread = threading.Thread(target=runner, daemon=True)
    thread.start()
    st.session_state["live_running"] = True


def render() -> None:
    setup_page("Configure & Run")
    components.page_header(
        crumbs=["Workflow", "Configure & Run"],
        title="Begin a new OCR job",
        sub=(
            "Drop a manuscript, choose an engine, and queue pages for "
            "processing. All settings map directly to ocr-hindi CLI flags."
        ),
    )

    # ── Source manuscript ────────────────────────────────────────────
    src_col, eng_col = st.columns([1.15, 1])

    with src_col:
        components.card_open(
            "Source manuscript",
            "PDF · processed page-by-page with crash-safe cache",
            ("badge-neutral", "STEP 1"),
        )
        uploaded = st.file_uploader(
            "Drop PDF here",
            type=["pdf"],
            label_visibility="collapsed",
            key="pdf_upload",
        )
        if uploaded is not None:
            saved = _save_uploaded(uploaded)
            st.session_state["uploaded_pdf"] = saved
            st.session_state["uploaded_pages"] = _detect_pages(saved)

        pdf_path: Path | None = st.session_state.get("uploaded_pdf")
        total_pages = int(st.session_state.get("uploaded_pages") or 0)

        if pdf_path:
            components.html(
                '<div style="border:1.5px dashed var(--border-warm);border-radius:10px;'
                'background:var(--bg);padding:18px;display:flex;align-items:center;gap:16px;margin-top:6px;">'
                '<div style="width:56px;height:64px;border-radius:4px;'
                "background:linear-gradient(180deg, var(--card) 0%, var(--surface-alt) 100%);"
                "border:1px solid var(--border-warm);box-shadow:var(--sh-1);"
                "display:grid;place-items:center;font-family:var(--font-deva);"
                'font-size:22px;color:var(--maroon-700)">॥</div>'
                '<div style="flex:1;">'
                f'<div style="font-size:14px;font-weight:600;color:var(--ink-900);">{pdf_path.name}</div>'
                f'<div class="mono" style="font-size:11.5px;color:var(--ink-500);margin-top:4px;">'
                f'{pdf_path.parent}  ·  <span style="color:var(--maroon-700)">{total_pages} pages</span>'
                "</div></div></div>"
            )
        else:
            st.info("Upload a PDF to begin. The file is staged in /tmp/ocr_uploads/.")

        components.html(
            '<div style="margin-top:18px;font-size:12px;font-weight:600;color:var(--ink-700);">'
            'Pages to process <span class="mono" style="color:var(--ink-400);font-weight:400;">--pages</span></div>'
        )
        page_preset = st.radio(
            "Pages preset",
            options=["all", "1-100", "1-500", "Custom"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
            key="page_preset",
        )
        if page_preset == "Custom":
            pages_spec = st.text_input(
                "Page range",
                value=st.session_state.get("pages_spec", "1-50"),
                key="pages_spec_input",
                label_visibility="collapsed",
                placeholder='e.g. "1-50, 120, 200-280"',
            )
        else:
            pages_spec = page_preset
        st.session_state["pages_spec"] = pages_spec

        st.caption('parses via parse_page_range() · matches "all", "1-50", "1,5,10-20"')

        # Selection preview
        if total_pages > 0:
            try:
                resolved = parse_page_range(pages_spec, total_pages)
                pct = len(resolved) / total_pages * 100
                components.html(
                    '<div style="margin-top:12px;">'
                    '<div style="display:flex;justify-content:space-between;font-size:11.5px;margin-bottom:6px;">'
                    '<span style="color:var(--ink-500);">Selection</span>'
                    '<span class="mono" style="color:var(--maroon-700);font-weight:600;">'
                    f"{len(resolved):,} / {total_pages:,} pages ({pct:.1f}%)"
                    "</span></div>"
                    '<div style="height:18px;background:var(--surface);border-radius:4px;'
                    'border:1px solid var(--border);overflow:hidden;">'
                    f'<div style="height:100%;width:{pct:.1f}%;background:var(--saffron-500);opacity:0.85;"></div>'
                    "</div></div>"
                )
            except ValueError as exc:
                st.error(f"Invalid page range: {exc}")
        components.card_close()

    with eng_col:
        components.card_open(
            "Engine",
            "choose backend · cost vs accuracy tradeoff",
            ("badge-neutral", "STEP 2"),
        )
        engine_id = st.radio(
            "Engine",
            options=[e.id for e in engines.ENGINES],
            format_func=lambda eid: f"{engines.ENGINES_BY_ID[eid].name} · {engines.ENGINES_BY_ID[eid].deva} · {engines.ENGINES_BY_ID[eid].cost}",
            key="engine",
            label_visibility="collapsed",
        )
        engine = engines.ENGINES_BY_ID[engine_id]
        st.markdown(
            f'<div style="margin-top:6px;color:var(--ink-500);font-size:12px;">'
            f'<span class="mono">{engine.flag}</span> · accuracy ~{engine.accuracy}% · '
            f"~{engine.speed_ppm} pages/min · {engine.ram} RAM</div>",
            unsafe_allow_html=True,
        )
        components.card_close()

    # ── Advanced parameters ──────────────────────────────────────────
    components.card_open(
        "Advanced parameters",
        "tune for your workload · sensible defaults inline",
        ("badge-neutral", "STEP 3"),
    )
    a, b, c, d = st.columns(4)
    with a:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:var(--ink-700);">'
            'Workers <span class="mono" style="color:var(--ink-400);font-weight:400;">--workers</span></div>',
            unsafe_allow_html=True,
        )
        workers = st.slider(
            "workers",
            1,
            20,
            st.session_state["workers"],
            label_visibility="collapsed",
            key="workers",
        )
        st.caption("Higher = faster, more memory · range 1–20")
    with b:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:var(--ink-700);">'
            'Confidence threshold <span class="mono" style="color:var(--ink-400);font-weight:400;">--confidence</span></div>',
            unsafe_allow_html=True,
        )
        confidence = st.slider(
            "confidence",
            0.0,
            1.0,
            st.session_state["confidence"],
            step=0.01,
            label_visibility="collapsed",
            key="confidence",
        )
        st.caption("Below this, hybrid mode escalates to Gemini")
    with c:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:var(--ink-700);">'
            'Render DPI <span class="mono" style="color:var(--ink-400);font-weight:400;">--dpi</span></div>',
            unsafe_allow_html=True,
        )
        dpi_options = [150, 200, 300, 400]
        dpi = st.selectbox(
            "dpi",
            dpi_options,
            index=dpi_options.index(st.session_state["dpi"])
            if st.session_state["dpi"] in dpi_options
            else 1,
            label_visibility="collapsed",
            key="dpi",
        )
        st.caption("Used by pdf2image.convert_from_path")
    with d:
        st.markdown(
            '<div style="font-size:12px;font-weight:600;color:var(--ink-700);">'
            'Output directory <span class="mono" style="color:var(--ink-400);font-weight:400;">-o</span></div>',
            unsafe_allow_html=True,
        )
        output_dir = st.text_input(
            "output dir",
            value=st.session_state["output_dir"],
            placeholder="default: <pdf>_output/",
            label_visibility="collapsed",
            key="output_dir",
        )
        st.caption("{stem}_unicode.md  ·  .ocr_cache_{stem}/")

    # toggles row
    t1, t2, t3, t4 = st.columns(4)
    with t1:
        verify = st.toggle(
            "Verify mantras with Gemini",
            value=st.session_state["verify_mantras"],
            key="verify_mantras",
        )
        st.caption("--verify-mantras · uses MantraDetector")
    with t2:
        resume = st.toggle("Resume from cache", value=st.session_state["resume"], key="resume")
        st.caption("--resume · skip cached pages")
    with t3:
        batch = st.toggle(
            "Vertex AI Batch (50% off)", value=st.session_state["use_batch"], key="use_batch"
        )
        st.caption("--batch · requires --gcs-bucket")
    with t4:
        dry = st.toggle("Dry run", value=st.session_state["dry_run"], key="dry_run")
        st.caption("--dry-run · preview only")

    if batch:
        st.text_input("GCS bucket", key="gcs_bucket", placeholder="gs://my-batch-bucket")
    components.card_close()

    # ── Estimate footer + submit ─────────────────────────────────────
    if pdf_path and total_pages > 0:
        try:
            resolved = parse_page_range(pages_spec, total_pages)
        except ValueError:
            resolved = []
    else:
        resolved = []

    cost = engines.estimate_cost(engine_id, len(resolved))
    minutes = engines.estimate_minutes(engine_id, len(resolved), workers)
    cost_str = f"${cost:.2f}" if cost else "$0.00"
    minutes_str = format_duration(minutes * 60) if minutes else "—"
    pages_per_min = (
        f"~{len(resolved) / minutes:.1f} pages/min · {workers} workers"
        if minutes
        else f"{workers} workers"
    )
    output_path_str = f"{(pdf_path.stem if pdf_path else 'output')}_unicode.md"
    cache_path_str = f".ocr_cache_{pdf_path.stem if pdf_path else 'output'}/"
    cost_delta = (
        f"— save ${(engines.estimate_cost('gemini', len(resolved)) - cost):.2f} vs pure Gemini"
        if cost > 0 and engine_id != "gemini"
        else "free local processing"
        if cost == 0
        else "pure Gemini path"
    )
    components.estimate_footer(
        cost=cost_str,
        cost_delta=cost_delta,
        time_estimate=minutes_str,
        pages_per_min=pages_per_min,
        output_path=output_path_str,
        cache_path=cache_path_str,
    )

    st.markdown('<div style="margin-top:18px;"></div>', unsafe_allow_html=True)
    submit_col, status_col = st.columns([1, 3])
    with submit_col:
        run_clicked = st.button(
            "Begin processing →",
            type="primary",
            use_container_width=True,
            disabled=not (pdf_path and resolved) or st.session_state.get("live_running", False),
        )
    with status_col:
        if st.session_state.get("live_running"):
            st.info("Processing in progress — open the **Live Processing** screen to watch.")
        elif st.session_state.get("last_error"):
            st.error(f"Last run failed: {st.session_state['last_error']}")

    if run_clicked and pdf_path and resolved:
        cfg = MultiProcessorConfig(
            backend=engine_id,
            dpi=dpi,
            max_concurrent=workers,
            confidence_threshold=confidence,
            detect_mantras=verify,
        )
        out_dir = state.output_dir_for(pdf_path)
        out_dir.mkdir(parents=True, exist_ok=True)
        st.session_state["last_pdf"] = pdf_path
        st.session_state["last_output_dir"] = out_dir
        st.session_state["last_error"] = None
        if dry:
            st.session_state["live_running"] = False
            st.success(
                f"Dry run: would process {len(resolved)} pages with {engine.name}. "
                f"Output → {out_dir / output_path_str}"
            )
        else:
            _start_job(pdf_path, resolved, cfg, out_dir, resume)
            st.success("Job started. Switch to **Live Processing** to monitor.")

    sidebar_footer()


if __name__ == "__main__":
    render()
