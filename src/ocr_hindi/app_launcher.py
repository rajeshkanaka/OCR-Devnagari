"""Launcher for the Streamlit OCR UI.

Invoked from the CLI as `ocr-hindi ui`. Locates the bundled
`ui/app.py` and runs it through the streamlit command line so that
the user gets the standard browser tab + autoreload behaviour.
"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:  # noqa: D401 - CLI entry point
    """Bootstraps Streamlit with the UI app file."""
    try:
        from streamlit.web import cli as st_cli
    except ImportError:
        sys.stderr.write(
            "Streamlit is not installed. Install with:\n"
            "  pip install 'ocr-devnagari[streamlit]'\n"
        )
        sys.exit(1)

    app_path = Path(__file__).parent / "ui" / "app.py"
    if not app_path.exists():
        sys.stderr.write(f"UI entry point not found: {app_path}\n")
        sys.exit(1)

    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--theme.base=light",
    ]
    sys.exit(st_cli.main())


if __name__ == "__main__":
    main()
