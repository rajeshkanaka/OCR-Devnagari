"""Session-state defaults and helpers for the Streamlit UI."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import streamlit as st

DEFAULTS: dict[str, Any] = {
    "theme": "Parchment",
    "deva_font": "Noto Serif Devanagari",
    # Configure screen
    "engine": "hybrid",
    "pages_spec": "all",
    "workers": 5,
    "confidence": 0.85,
    "dpi": 200,
    "output_dir": "",
    "verify_mantras": True,
    "resume": True,
    "use_batch": False,
    "dry_run": False,
    "gcs_bucket": "",
    "uploaded_pdf": None,  # Path | None
    "uploaded_pages": 0,
    # Live-screen polling
    "live_running": False,
    "current_page": 1,
    # Job history (Path of last processed PDF)
    "last_pdf": None,
    "last_output_dir": None,
}


def init_state() -> None:
    """Ensure all expected session keys are present with default values."""
    for key, value in DEFAULTS.items():
        st.session_state.setdefault(key, value)


def env_summary() -> dict[str, str]:
    """Read the relevant environment variables for the auth screen."""
    return {
        "GOOGLE_GENAI_USE_VERTEXAI": os.environ.get("GOOGLE_GENAI_USE_VERTEXAI", ""),
        "GOOGLE_CLOUD_PROJECT": os.environ.get("GOOGLE_CLOUD_PROJECT", ""),
        "GOOGLE_CLOUD_LOCATION": os.environ.get("GOOGLE_CLOUD_LOCATION", ""),
        "GEMINI_API_KEY": "set" if os.environ.get("GEMINI_API_KEY") else "",
    }


def auth_status() -> tuple[str, str]:
    """Return (kind, label) describing the active auth method.

    kind ∈ {"vertex", "api_key", "none"}
    """
    env = env_summary()
    if env["GOOGLE_GENAI_USE_VERTEXAI"] == "1" and env["GOOGLE_CLOUD_PROJECT"]:
        return "vertex", "Vertex AI"
    if env["GEMINI_API_KEY"]:
        return "api_key", "API Key"
    return "none", "Not configured"


def output_dir_for(pdf_path: Path | None) -> Path:
    """Return the resolved output directory for a given PDF, or a sensible default."""
    user_dir = (st.session_state.get("output_dir") or "").strip()
    if user_dir:
        return Path(user_dir).expanduser()
    if pdf_path is not None:
        return pdf_path.parent / f"{pdf_path.stem}_output"
    return Path.cwd() / "ocr_output"
