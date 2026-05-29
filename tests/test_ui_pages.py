"""Smoke-test that every Streamlit page renders without exceptions."""

from __future__ import annotations

from streamlit.testing.v1 import AppTest


def _run(path: str) -> None:
    at = AppTest.from_file(path, default_timeout=30)
    at.run()
    assert not at.exception, [str(e) for e in at.exception]


def test_configure_screen_renders() -> None:
    _run("src/ocr_hindi/ui/pages/configure.py")


def test_engines_screen_renders() -> None:
    _run("src/ocr_hindi/ui/pages/engines_screen.py")


def test_live_screen_renders() -> None:
    _run("src/ocr_hindi/ui/pages/live.py")


def test_results_screen_renders() -> None:
    _run("src/ocr_hindi/ui/pages/results.py")


def test_setup_screen_renders() -> None:
    _run("src/ocr_hindi/ui/pages/setup_screen.py")


def test_engine_metadata_complete() -> None:
    """Sanity check the static engine metadata table."""
    from ocr_hindi.ui.engines import ENGINES, ENGINES_BY_ID, estimate_cost, estimate_minutes

    assert {e.id for e in ENGINES} == {
        "hybrid",
        "easyocr",
        "marker",
        "chandra",
        "tesseract",
        "gemini",
    }
    # Default engine is featured
    assert ENGINES_BY_ID["hybrid"].featured

    # Free engines have zero cost
    for free_id in ("easyocr", "marker", "tesseract", "chandra"):
        assert estimate_cost(free_id, 1000) == 0.0

    # Cost grows with pages
    assert estimate_cost("gemini", 1000) > estimate_cost("gemini", 100)
    # Time estimate is positive for any non-zero workload
    assert estimate_minutes("hybrid", 100, 8) > 0


def test_themes_loaded() -> None:
    from ocr_hindi.ui.theme import DEVA_FONTS, THEMES

    assert set(THEMES.keys()) == {"Parchment", "Light scriptorium", "Dark scriptorium"}
    assert "Noto Serif Devanagari" in DEVA_FONTS
