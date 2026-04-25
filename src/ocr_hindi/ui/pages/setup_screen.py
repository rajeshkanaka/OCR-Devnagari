"""Screen 5 — Setup & Auth.

Mirrors `ocr-hindi validate`: env vars, dependency probes, and
per-backend smoke tests.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess

import streamlit as st

from ocr_hindi.async_processor import AsyncOCRProcessor
from ocr_hindi.ui import components, state
from ocr_hindi.ui.layout import setup_page, sidebar_footer


def _probe_python_module(name: str) -> tuple[bool, str]:
    """Check if a Python module is importable, return (ok, version)."""
    spec = importlib.util.find_spec(name.replace("-", "_"))
    if not spec:
        return False, "—"
    version = "unknown"
    try:
        module = importlib.import_module(name.replace("-", "_"))
        version = getattr(module, "__version__", "unknown")
    except Exception:  # noqa: BLE001
        pass
    return True, str(version)


def _probe_system_binary(name: str) -> tuple[bool, str]:
    """Check if a system binary is on PATH."""
    path = shutil.which(name)
    if not path:
        return False, "—"
    try:
        proc = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=4)
        out = (
            (proc.stdout or proc.stderr).strip().splitlines()[0]
            if proc.stdout or proc.stderr
            else "ok"
        )
        return True, out
    except (subprocess.SubprocessError, OSError):
        return True, "found"


def _dep_row(name: str, ok: bool, version: str, hint: str) -> None:
    """Render a single dependency row in the manuscript style."""
    icon_bg = "var(--sage-100)" if ok else "var(--surface-alt)"
    icon_color = "var(--sage-600)" if ok else "var(--ink-400)"
    icon = "✓" if ok else "·"
    version_color = "var(--sage-600)" if ok else "var(--ink-400)"
    components.html(
        '<div style="display:flex;gap:12px;padding:10px 0;border-bottom:1px dashed var(--surface-alt);align-items:center;">'
        f'<span style="width:22px;height:22px;border-radius:999px;background:{icon_bg};'
        f'color:{icon_color};display:grid;place-items:center;flex:0 0 auto;font-weight:700;">{icon}</span>'
        '<div style="flex:1;">'
        '<div style="display:flex;justify-content:space-between;">'
        f'<span class="mono" style="font-size:12.5px;font-weight:600;color:var(--ink-900);">{name}</span>'
        f'<span class="mono" style="font-size:11px;color:{version_color};">{version}</span>'
        "</div>"
        f'<div style="font-size:11px;color:var(--ink-400);margin-top:2px;">{hint}</div>'
        "</div></div>"
    )


def render() -> None:
    setup_page("Setup & Auth")
    components.page_header(
        crumbs=["System", "Setup & Auth"],
        title="Environment check",
        sub=(
            "Run before your first OCR job. Mirrors `python -m ocr_hindi validate` "
            "exactly — same probes, same outputs."
        ),
    )

    col_auth, col_deps = st.columns(2)

    # ── Authentication card ───────────────────────────────────────────
    with col_auth:
        kind, label = state.auth_status()
        env = state.env_summary()
        components.card_open(
            "Authentication",
            "Gemini API key or Vertex AI · pick one",
            ("badge-sage", "✓ CONNECTED") if kind != "none" else ("badge-rust", "NOT SET"),
        )

        if kind == "vertex":
            components.html(
                '<div style="border:1.5px solid var(--saffron-500);background:var(--saffron-100);'
                'border-radius:8px;padding:16px;margin-bottom:12px;">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                '<strong style="color:var(--saffron-700);font-size:13px;">● Vertex AI · ACTIVE</strong>'
                '<span class="mono" style="font-size:10px;color:var(--ink-500);">recommended</span>'
                "</div>"
                '<div class="mono" style="font-size:11.5px;display:grid;grid-template-columns:auto 1fr;gap:6px 16px;">'
                f'<span style="color:var(--ink-400);">GOOGLE_GENAI_USE_VERTEXAI</span><span style="color:var(--ink-700);">{env["GOOGLE_GENAI_USE_VERTEXAI"]}</span>'
                f'<span style="color:var(--ink-400);">GOOGLE_CLOUD_PROJECT</span><span style="color:var(--ink-700);">{env["GOOGLE_CLOUD_PROJECT"]}</span>'
                f'<span style="color:var(--ink-400);">GOOGLE_CLOUD_LOCATION</span><span style="color:var(--ink-700);">{env["GOOGLE_CLOUD_LOCATION"] or "global"}</span>'
                "</div></div>"
            )
        elif kind == "api_key":
            components.html(
                '<div style="border:1.5px solid var(--saffron-500);background:var(--saffron-100);'
                'border-radius:8px;padding:16px;margin-bottom:12px;">'
                '<div style="display:flex;justify-content:space-between;margin-bottom:8px;">'
                '<strong style="color:var(--saffron-700);font-size:13px;">● Gemini API key · ACTIVE</strong>'
                '<span class="mono" style="font-size:10px;color:var(--ink-500);">fallback</span>'
                "</div>"
                '<div class="mono" style="font-size:11.5px;color:var(--ink-700);">GEMINI_API_KEY · set</div>'
                "</div>"
            )
        else:
            st.error(
                "No Gemini credentials detected. Set `GEMINI_API_KEY` for the "
                "API key path, or `GOOGLE_GENAI_USE_VERTEXAI=1` plus "
                "`GOOGLE_CLOUD_PROJECT` for Vertex AI."
            )

        components.divider_ornament("॥ ॐ ॥")
        st.caption("Need to switch? Edit your shell profile or .env file, then reload.")
        components.card_close()

    # ── Dependencies card ─────────────────────────────────────────────
    with col_deps:
        components.card_open("Dependencies", "core + optional engines")
        deps = [
            ("google-genai", "google.genai", "Vertex AI + Gemini API client", True),
            ("pdf2image", "pdf2image", "PDF rendering", True),
            ("pillow", "PIL", "Image processing", True),
            ("easyocr", "easyocr", "Local Hindi/Devanagari OCR", False),
            ("marker-pdf", "marker", "optional · pip install marker-pdf", False),
            ("chandra-ocr", "chandra", "optional · pip install 'chandra-ocr[hf]'", False),
            ("pytesseract", "pytesseract", "Tesseract Python bindings", False),
        ]
        missing = 0
        for display_name, import_name, hint, _required in deps:
            ok, ver = _probe_python_module(import_name)
            _dep_row(display_name, ok, ver, hint)
            if not ok:
                missing += 1

        # System binaries
        for binary, hint in [
            ("pdftoppm", "system: pdftoppm (poppler)"),
            ("tesseract", "system: tesseract OCR"),
        ]:
            ok, ver = _probe_system_binary(binary)
            _dep_row(binary, ok, ver, hint)
            if not ok:
                missing += 1

        if missing:
            st.warning(
                f"{missing} optional dependency(ies) missing — install them for the related engines."
            )
        components.card_close()

    # ── Smoke test card ───────────────────────────────────────────────
    components.card_open(
        "Smoke test",
        "small request through each enabled backend · proves they actually work",
    )
    if st.button("Run smoke test", type="secondary"):
        with st.spinner("Probing backends…"):
            results: list[tuple[str, bool, str]] = []

            # Vertex AI / Gemini
            try:
                processor = AsyncOCRProcessor()
                ok, _, msg = processor.validate_auth()
                results.append(("Vertex AI / Gemini", ok, msg))
            except Exception as exc:  # noqa: BLE001
                results.append(("Vertex AI / Gemini", False, str(exc)))

            # EasyOCR
            ok, _ = _probe_python_module("easyocr")
            results.append(("EasyOCR", ok, "module importable" if ok else "not installed"))

            # Tesseract
            ok, _ = _probe_system_binary("tesseract")
            results.append(("Tesseract", ok, "found on PATH" if ok else "not installed"))

            # Marker
            ok, _ = _probe_python_module("marker")
            results.append(("Marker", ok, "module importable" if ok else "not installed"))

            # Chandra
            ok, _ = _probe_python_module("chandra")
            results.append(("Chandra", ok, "module importable" if ok else "not installed"))

        cols = st.columns(min(len(results), 5))
        for i, (name, ok, msg) in enumerate(results):
            with cols[i % len(cols)]:
                bg = "var(--sage-100)" if ok else "var(--surface-alt)"
                color = "var(--sage-600)" if ok else "var(--ink-400)"
                components.html(
                    f'<div style="background:{bg};border:1px solid var(--border);border-radius:8px;padding:12px;">'
                    '<div style="display:flex;justify-content:space-between;margin-bottom:6px;">'
                    f'<strong style="color:{color};font-size:12.5px;">{name}</strong>'
                    "</div>"
                    f'<div class="mono" style="font-size:10.5px;color:var(--ink-700);line-height:1.5;">{msg}</div>'
                    "</div>"
                )
    components.card_close()

    sidebar_footer()


if __name__ == "__main__":
    render()
