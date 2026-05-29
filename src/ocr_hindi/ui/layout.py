"""Common page-setup boilerplate used by every screen."""

from __future__ import annotations

import streamlit as st

from . import components, state, theme


def setup_page(page_label: str) -> None:
    """Apply Streamlit page config, theme, sidebar brand and tweaks panel."""
    st.set_page_config(
        page_title=f"OCR Devnagari · {page_label}",
        page_icon="ॐ",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    state.init_state()
    theme.apply_theme(
        st.session_state.get("theme", "Parchment"),
        st.session_state.get("deva_font", "Noto Serif Devanagari"),
    )
    with st.sidebar:
        components.sidebar_brand()


def sidebar_footer() -> None:
    """Render the always-visible session card + tweaks panel inside the sidebar."""
    with st.sidebar:
        kind, label = state.auth_status()
        env = state.env_summary()
        components.sidebar_session_card(
            project=env["GOOGLE_CLOUD_PROJECT"] or "—",
            auth=label,
            spend_today="$0.00",
        )
        components.tweaks_panel()
