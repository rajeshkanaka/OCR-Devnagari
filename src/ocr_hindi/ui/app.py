"""Streamlit multipage entry point.

Run via:
    streamlit run src/ocr_hindi/ui/app.py
or via the helper:
    ocr-hindi ui    (which calls ocr_hindi.app_launcher:main)
"""

from __future__ import annotations

import streamlit as st

from ocr_hindi.ui.pages import configure as configure_page
from ocr_hindi.ui.pages import engines_screen as engines_page
from ocr_hindi.ui.pages import live as live_page
from ocr_hindi.ui.pages import results as results_page
from ocr_hindi.ui.pages import setup_screen as setup_page


def _build_navigation() -> st.navigation:  # type: ignore[name-defined]
    """Compose the multipage navigation tree."""
    return st.navigation(
        {
            "Workflow": [
                st.Page(
                    configure_page.render,
                    title="Configure & Run",
                    icon=":material/play_arrow:",
                    url_path="configure",
                    default=True,
                ),
                st.Page(
                    engines_page.render,
                    title="Engines",
                    icon=":material/auto_awesome:",
                    url_path="engines",
                ),
                st.Page(
                    live_page.render,
                    title="Live Processing",
                    icon=":material/sync:",
                    url_path="live",
                ),
                st.Page(
                    results_page.render,
                    title="Results Viewer",
                    icon=":material/article:",
                    url_path="results",
                ),
            ],
            "System": [
                st.Page(
                    setup_page.render,
                    title="Setup & Auth",
                    icon=":material/settings:",
                    url_path="setup",
                ),
            ],
        }
    )


def main() -> None:
    """Streamlit entry point."""
    nav = _build_navigation()
    nav.run()


main()
