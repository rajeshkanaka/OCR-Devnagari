"""Manuscript-inspired theme tokens and Streamlit CSS injection.

Maps 1:1 to the design system in
.context/design/ocr-project-ui/project/styles.css.
"""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st


# --- Devanagari display fonts available in the tweaks panel -------------------
DEVA_FONTS: dict[str, str] = {
    "Noto Serif Devanagari": '"Noto Serif Devanagari", serif',
    "Tiro Devanagari Sanskrit": '"Tiro Devanagari Sanskrit", serif',
    "Tiro Devanagari Hindi": '"Tiro Devanagari Hindi", serif',
    "Noto Sans Devanagari": '"Noto Sans Devanagari", sans-serif',
    "Sanskrit Text": '"Sanskrit Text", serif',
}


@dataclass(frozen=True)
class Palette:
    """Palette tokens for one of the available themes."""

    bg: str
    surface: str
    card: str
    surface_alt: str
    border: str
    border_warm: str
    ink_900: str
    ink_700: str
    ink_500: str
    ink_400: str
    ink_300: str
    saffron_500: str
    saffron_600: str
    saffron_700: str
    saffron_100: str
    maroon_700: str
    maroon_500: str
    maroon_100: str
    gold_600: str
    gold_400: str
    gold_100: str
    sage_600: str
    sage_100: str
    rust_600: str
    rust_100: str


PARCHMENT = Palette(
    bg="#fbf6ec",
    surface="#f5ecd7",
    card="#fffaf0",
    surface_alt="#ecdfc1",
    border="#ddc89a",
    border_warm="#b8a173",
    ink_900="#1a1410",
    ink_700="#3a2c20",
    ink_500="#6b5642",
    ink_400="#8a755e",
    ink_300="#a89178",
    saffron_500="#c8551d",
    saffron_600="#a8451a",
    saffron_700="#883415",
    saffron_100="#f7e3d2",
    maroon_700="#6b2410",
    maroon_500="#8a3318",
    maroon_100="#f0d9cc",
    gold_600="#a8821e",
    gold_400="#c9a84a",
    gold_100="#f3e8c4",
    sage_600="#4a6b3e",
    sage_100="#dee8d3",
    rust_600="#9a4a1f",
    rust_100="#f5e0d0",
)

LIGHT = Palette(
    bg="#ffffff",
    surface="#f7f7f5",
    card="#ffffff",
    surface_alt="#eeeeea",
    border="#d8d4cd",
    border_warm="#b9b3a8",
    ink_900="#0d0d0d",
    ink_700="#262626",
    ink_500="#4d4d4d",
    ink_400="#737373",
    ink_300="#9c9c9c",
    saffron_500="#c8551d",
    saffron_600="#a8451a",
    saffron_700="#883415",
    saffron_100="#fbe8d7",
    maroon_700="#6b2410",
    maroon_500="#8a3318",
    maroon_100="#f3dcd0",
    gold_600="#a8821e",
    gold_400="#c9a84a",
    gold_100="#f5e8b8",
    sage_600="#3f6638",
    sage_100="#dde8d6",
    rust_600="#9a4a1f",
    rust_100="#f5e0d0",
)

DARK = Palette(
    bg="#1a1410",
    surface="#22191a",
    card="#2a201d",
    surface_alt="#33271f",
    border="#4d3a2c",
    border_warm="#6b5642",
    ink_900="#fbf6ec",
    ink_700="#ecdfc1",
    ink_500="#b8a173",
    ink_400="#8a755e",
    ink_300="#6b5642",
    saffron_500="#e07a3f",
    saffron_600="#c8551d",
    saffron_700="#a8451a",
    saffron_100="#3a2418",
    maroon_700="#c46442",
    maroon_500="#a8451a",
    maroon_100="#3a2418",
    gold_600="#d4b454",
    gold_400="#c9a84a",
    gold_100="#3a2e18",
    sage_600="#a8c498",
    sage_100="#2a3a22",
    rust_600="#d97a4a",
    rust_100="#3a2418",
)

THEMES: dict[str, Palette] = {
    "Parchment": PARCHMENT,
    "Light scriptorium": LIGHT,
    "Dark scriptorium": DARK,
}


def apply_theme(theme_name: str = "Parchment", deva_font: str = "Noto Serif Devanagari") -> Palette:
    """Inject the manuscript theme CSS into the current Streamlit page.

    Returns the active palette for direct color reuse in callers.

    Uses st.markdown(unsafe_allow_html=True) — Streamlit allows `<style>` tags
    via that path, but every line must be flush-left (Markdown promotes 4-space
    indented lines to <pre> blocks, which leaks CSS as plain text).
    """
    palette = THEMES.get(theme_name, PARCHMENT)
    deva_stack = DEVA_FONTS.get(deva_font, DEVA_FONTS["Noto Serif Devanagari"])
    css = _build_css(palette, deva_stack)
    flat = "\n".join(line.strip() for line in css.splitlines())
    st.markdown(flat, unsafe_allow_html=True)
    return palette


def _build_css(p: Palette, deva_stack: str) -> str:
    """Build the full <style> block. Kept as one string to minimise re-injection."""
    return f"""
<style>
@import url("https://fonts.googleapis.com/css2?family=Tiro+Devanagari+Sanskrit:ital@0;1&family=Tiro+Devanagari+Hindi:ital@0;1&family=Noto+Serif+Devanagari:wght@400;500;600;700&family=Noto+Sans+Devanagari:wght@400;500;600;700&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap");

:root {{
    --bg: {p.bg};
    --surface: {p.surface};
    --card: {p.card};
    --surface-alt: {p.surface_alt};
    --border: {p.border};
    --border-warm: {p.border_warm};
    --ink-900: {p.ink_900};
    --ink-700: {p.ink_700};
    --ink-500: {p.ink_500};
    --ink-400: {p.ink_400};
    --ink-300: {p.ink_300};
    --saffron-500: {p.saffron_500};
    --saffron-600: {p.saffron_600};
    --saffron-700: {p.saffron_700};
    --saffron-100: {p.saffron_100};
    --maroon-700: {p.maroon_700};
    --maroon-500: {p.maroon_500};
    --maroon-100: {p.maroon_100};
    --gold-600: {p.gold_600};
    --gold-400: {p.gold_400};
    --gold-100: {p.gold_100};
    --sage-600: {p.sage_600};
    --sage-100: {p.sage_100};
    --rust-600: {p.rust_600};
    --rust-100: {p.rust_100};
    --font-display: "Cormorant Garamond", "Iowan Old Style", Georgia, serif;
    --font-body: "Inter", -apple-system, BlinkMacSystemFont, sans-serif;
    --font-deva: {deva_stack};
    --font-mono: "JetBrains Mono", "SF Mono", Menlo, monospace;
    --r-sm: 4px; --r-md: 8px; --r-lg: 12px;
    --sh-1: 0 1px 2px rgba(58, 44, 32, 0.06), 0 1px 1px rgba(58, 44, 32, 0.04);
    --sh-2: 0 2px 6px rgba(58, 44, 32, 0.08), 0 1px 2px rgba(58, 44, 32, 0.06);
    --sh-3: 0 8px 24px rgba(58, 44, 32, 0.10), 0 2px 6px rgba(58, 44, 32, 0.06);
}}

/* ── App shell ───────────────────────────────────────────────────────── */
html, body, [class*="stApp"] {{
    background: var(--bg) !important;
    color: var(--ink-900);
    font-family: var(--font-body);
    -webkit-font-smoothing: antialiased;
}}
.main .block-container {{
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    max-width: 1240px;
}}

/* ── Sidebar ─────────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, var(--surface) 0%, var(--bg) 100%);
    border-right: 1px solid var(--border);
}}
section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {{
    padding-top: 1.25rem;
}}

/* ── Typography ──────────────────────────────────────────────────────── */
.stApp h1, .stApp h2, .stApp h3, .stApp h4,
[data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
.page-title, .ocr-card-title, .engine-name, .stat-value {{
    font-family: var(--font-display) !important;
    color: var(--ink-900);
    letter-spacing: -0.005em;
}}
h1.page-title {{ font-weight: 600 !important; font-size: 36px !important; line-height: 1.05 !important; margin: 0 0 12px !important; }}
.deva, .deva-text {{ font-family: var(--font-deva) !important; }}
code, pre, kbd, samp, .mono {{ font-family: var(--font-mono) !important; }}

/* ── Card primitive (used via components.card_*) ─────────────────────── */
.ocr-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    box-shadow: var(--sh-1);
    padding: 24px;
    margin-bottom: 16px;
}}
.ocr-card-header {{
    display: flex; justify-content: space-between; align-items: flex-start;
    gap: 16px; margin-bottom: 16px;
    padding-bottom: 14px; border-bottom: 1px solid var(--surface-alt);
}}
.ocr-card-title {{
    font-family: var(--font-display);
    font-size: 19px; font-weight: 600;
    color: var(--ink-900); margin: 0; line-height: 1.2;
}}
.ocr-card-sub {{ font-size: 12.5px; color: var(--ink-500); margin-top: 2px; }}

/* ── Page header ─────────────────────────────────────────────────────── */
.page-eyebrow {{
    font-family: var(--font-mono);
    font-size: 10.5px;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: var(--ink-400);
    margin-bottom: 6px;
}}
.page-eyebrow span:not(:first-child)::before {{
    content: " / "; color: var(--border-warm); margin: 0 6px;
}}
.page-title {{
    font-family: var(--font-display);
    font-size: 36px; font-weight: 600; line-height: 1.05;
    color: var(--ink-900); margin: 0 0 6px;
}}
.page-sub {{
    font-size: 15px; color: var(--ink-500);
    max-width: 720px; line-height: 1.5; margin: 0 0 20px;
}}

/* ── Brand mark in sidebar ───────────────────────────────────────────── */
.brand-row {{ display: flex; align-items: center; gap: 12px; padding-bottom: 16px; border-bottom: 1px solid var(--border); margin-bottom: 18px; }}
.brand-mark {{
    width: 38px; height: 38px;
    border-radius: 8px;
    background: linear-gradient(135deg, var(--saffron-500) 0%, var(--maroon-700) 100%);
    color: var(--bg);
    display: grid; place-items: center;
    font-family: var(--font-deva);
    font-size: 22px; font-weight: 600; line-height: 1;
    box-shadow: var(--sh-1);
}}
.brand-name {{
    font-family: var(--font-display); font-weight: 600; font-size: 18px;
    color: var(--ink-900); line-height: 1.1;
}}
.brand-sub {{
    font-family: var(--font-mono); font-size: 10px;
    color: var(--ink-400); letter-spacing: 0.06em;
    text-transform: uppercase; margin-top: 2px;
}}

/* ── Badges ──────────────────────────────────────────────────────────── */
.badge {{
    display: inline-flex; align-items: center; gap: 5px;
    padding: 3px 8px; border-radius: 999px;
    font-family: var(--font-mono);
    font-size: 10.5px; font-weight: 600;
    letter-spacing: 0.04em; text-transform: uppercase; line-height: 1;
}}
.badge-saffron {{ background: var(--saffron-100); color: var(--saffron-700); }}
.badge-maroon {{ background: var(--maroon-100); color: var(--maroon-700); }}
.badge-sage {{ background: var(--sage-100); color: var(--sage-600); }}
.badge-gold {{ background: var(--gold-100); color: var(--gold-600); }}
.badge-rust {{ background: var(--rust-100); color: var(--rust-600); }}
.badge-neutral {{ background: var(--surface-alt); color: var(--ink-500); }}

/* ── Stat tile ───────────────────────────────────────────────────────── */
.stat {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 16px 20px;
}}
.stat-label {{
    font-family: var(--font-mono);
    font-size: 10px; letter-spacing: 0.10em;
    text-transform: uppercase; color: var(--ink-400);
    margin-bottom: 4px;
}}
.stat-value {{
    font-family: var(--font-display);
    font-size: 28px; font-weight: 600;
    color: var(--ink-900); line-height: 1.1;
    letter-spacing: -0.01em;
}}
.stat-delta {{
    font-family: var(--font-mono);
    font-size: 11px; color: var(--sage-600);
    margin-top: 4px;
}}

/* ── Engine card ─────────────────────────────────────────────────────── */
.engine-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r-lg);
    padding: 20px;
    box-shadow: var(--sh-1);
    height: 100%;
    position: relative;
}}
.engine-card.featured {{
    border: 1.5px solid var(--saffron-500);
}}
.engine-card .featured-pill {{
    position: absolute; top: -10px; left: 18px;
    background: var(--saffron-500); color: white;
    font-family: var(--font-mono); font-size: 9px; font-weight: 700;
    letter-spacing: 0.12em; padding: 3px 10px; border-radius: 999px;
}}
.engine-name {{
    font-family: var(--font-display); font-size: 22px; font-weight: 600;
    color: var(--ink-900); line-height: 1.1;
}}
.engine-deva {{ font-family: var(--font-deva); font-size: 14px; color: var(--maroon-700); margin-top: 2px; }}
.engine-desc {{ font-size: 12.5px; color: var(--ink-700); line-height: 1.55; margin: 8px 0 14px; min-height: 56px; }}
.engine-stat {{ border-left: 2px solid var(--border); padding-left: 8px; }}
.engine-stat .label {{ font-family: var(--font-mono); font-size: 9px; color: var(--ink-400); letter-spacing: 0.08em; }}
.engine-stat .value {{ font-family: var(--font-display); font-size: 16px; font-weight: 600; color: var(--ink-900); }}
.engine-stat .value.free {{ color: var(--sage-600); }}

/* ── Streamlit widget tweaks ─────────────────────────────────────────── */
button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
    background: var(--saffron-500) !important;
    border-color: var(--saffron-500) !important;
    color: var(--bg) !important;
    font-weight: 600;
    border-radius: var(--r-md) !important;
}}
button[kind="primary"]:hover {{
    background: var(--saffron-600) !important;
    border-color: var(--saffron-600) !important;
}}
.stButton > button {{
    border-radius: var(--r-md);
    font-weight: 500;
    border-color: var(--border);
}}
.stProgress > div > div > div > div {{
    background: linear-gradient(90deg, var(--saffron-500) 0%, var(--maroon-700) 100%);
}}
.stRadio label, .stCheckbox label {{ color: var(--ink-700); }}
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stSelectbox div[role="combobox"] {{
    background: var(--card) !important;
    border: 1px solid var(--border) !important;
    color: var(--ink-900) !important;
    border-radius: var(--r-md) !important;
}}
.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    font-family: var(--font-body);
    font-weight: 500;
}}
[data-testid="stMetricLabel"] {{
    font-family: var(--font-mono);
    font-size: 10px !important;
    letter-spacing: 0.10em;
    text-transform: uppercase;
    color: var(--ink-400) !important;
}}
[data-testid="stMetricValue"] {{
    font-family: var(--font-display);
    color: var(--ink-900) !important;
}}

/* ── Mantra alert strip ──────────────────────────────────────────────── */
.mantra-strip {{
    display: flex; gap: 10px; align-items: center;
    padding: 10px 14px; margin: 8px 0 14px;
    background: var(--maroon-100);
    border: 1px solid rgba(106, 36, 16, 0.2);
    border-radius: 6px;
}}
.mantra-strip .glyph {{ font-family: var(--font-deva); font-size: 18px; color: var(--maroon-700); }}
.mantra-strip .text {{ font-size: 12.5px; color: var(--maroon-700); line-height: 1.4; }}

/* ── Log stream ──────────────────────────────────────────────────────── */
.log-stream {{
    background: #1a1410; color: #ecdfc1;
    border-radius: var(--r-md);
    padding: 16px; font-family: var(--font-mono);
    font-size: 11px; line-height: 1.65;
    max-height: 360px; overflow-y: auto;
}}
.log-stream .ts {{ color: #a89178; }}
.log-stream .lvl-INFO {{ color: var(--sage-600); }}
.log-stream .lvl-WARN {{ color: var(--rust-600); }}
.log-stream .lvl-ERROR {{ color: var(--rust-600); }}
.log-stream .lvl-MANTRA {{ color: var(--maroon-700); }}
.log-stream .lvl-OCR {{ color: var(--saffron-500); }}

/* ── Atlas grid cell ─────────────────────────────────────────────────── */
.atlas {{ display: grid; grid-template-columns: repeat(32, 1fr); gap: 3px; }}
.atlas .cell {{ aspect-ratio: 1; border-radius: 2px; }}
.atlas .easyocr {{ background: var(--sage-600); }}
.atlas .gemini {{ background: var(--saffron-500); }}
.atlas .mantra {{ background: var(--maroon-700); }}
.atlas .failed {{ background: var(--rust-600); }}
.atlas .active {{ background: var(--gold-400); animation: pulse 1.4s ease-in-out infinite; }}
.atlas .pending {{ background: var(--border); }}
@keyframes pulse {{ 0%, 100% {{ opacity: 1 }} 50% {{ opacity: 0.4 }} }}

/* ── Devanagari content area ─────────────────────────────────────────── */
.deva-block {{
    font-family: var(--font-deva);
    line-height: 1.85;
    color: var(--ink-900);
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    padding: 24px 28px;
    font-size: 16px;
}}
.deva-block .center {{ text-align: center; color: var(--maroon-700); }}

/* ── Divider ornament ────────────────────────────────────────────────── */
.divider-ornament {{
    display: flex; align-items: center; gap: 12px;
    color: var(--border-warm); margin: 20px 0;
}}
.divider-ornament::before, .divider-ornament::after {{
    content: ""; flex: 1; height: 1px; background: var(--border);
}}
.divider-ornament .glyph {{
    font-family: var(--font-deva); font-size: 14px; color: var(--gold-600);
}}

/* hide Streamlit's default header chrome we don't want */
header[data-testid="stHeader"] {{ background: transparent; }}
#MainMenu {{ visibility: visible; }}

/* footnote in sidebar */
.sidebar-foot {{
    margin-top: 16px; padding-top: 16px;
    border-top: 1px solid var(--border);
    font-family: var(--font-mono);
    font-size: 11px; color: var(--ink-500); line-height: 1.7;
}}
.sidebar-foot .row {{ display: flex; justify-content: space-between; }}
.sidebar-foot .row .val {{ color: var(--ink-700); }}
</style>
"""
