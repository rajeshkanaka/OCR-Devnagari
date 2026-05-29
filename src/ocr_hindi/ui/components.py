"""Reusable UI primitives for the Streamlit OCR app.

These are pure helpers that emit HTML using ``st.markdown(unsafe_allow_html=True)``
to recreate the manuscript design system from styles.css.

Important: every HTML payload is collapsed to a single line so Markdown's
4-space-indent rule doesn't turn it into a literal code block.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from html import escape

import streamlit as st

from . import theme


def html(payload: str) -> None:
    """Send a raw HTML payload to Streamlit, stripped of leading whitespace per line.

    Markdown promotes any line that starts with 4+ spaces to a code block;
    that turns our raw HTML into visible source text. By stripping the
    indentation introduced by Python f-strings we keep Streamlit happy.
    """
    flat = re.sub(r"\n\s+", "", payload).strip()
    st.markdown(flat, unsafe_allow_html=True)


# Backwards-compatible alias used internally
_emit = html


def page_header(*, crumbs: Iterable[str], title: str, sub: str | None = None) -> None:
    """Render the standard page header with breadcrumb, title and subtitle."""
    crumbs_html = "".join(f"<span>{escape(c)}</span>" for c in crumbs)
    sub_html = f'<p class="page-sub">{escape(sub)}</p>' if sub else ""
    _emit(
        f'<div style="margin-bottom:24px;">'
        f'<div class="page-eyebrow">{crumbs_html}</div>'
        f'<h1 class="page-title">{escape(title)}</h1>'
        f"{sub_html}"
        f"</div>"
    )


def card_open(title: str, sub: str | None = None, badge: tuple[str, str] | None = None) -> None:
    """Open a styled card. Caller must call card_close() afterwards.

    `badge` is an optional (css_class, label) tuple. css_class is one of
    "badge-saffron", "badge-sage", "badge-rust", etc.
    """
    badge_html = ""
    if badge:
        cls, label = badge
        badge_html = f'<span class="badge {escape(cls)}">{escape(label)}</span>'
    sub_html = f'<div class="ocr-card-sub">{escape(sub)}</div>' if sub else ""
    _emit(
        '<div class="ocr-card">'
        '<div class="ocr-card-header">'
        f'<div><h3 class="ocr-card-title">{escape(title)}</h3>{sub_html}</div>'
        f"{badge_html}"
        "</div>"
    )


def card_close() -> None:
    """Close a previously opened card div."""
    _emit("</div>")


def stat_tile(
    label: str, value: str, *, delta: str | None = None, accent: str | None = None
) -> None:
    """Render a stat tile in the manuscript style."""
    color = f"color:{accent};" if accent else ""
    delta_html = f'<div class="stat-delta">{escape(delta)}</div>' if delta else ""
    _emit(
        '<div class="stat">'
        f'<div class="stat-label">{escape(label)}</div>'
        f'<div class="stat-value" style="{color}">{value}</div>'
        f"{delta_html}"
        "</div>"
    )


def badge(label: str, kind: str = "neutral") -> str:
    """Return inline HTML for a badge for use inside another HTML block."""
    return f'<span class="badge badge-{escape(kind)}">{escape(label)}</span>'


def mantra_alert(message: str) -> None:
    """Render the maroon mantra-detected alert strip."""
    _emit(
        '<div class="mantra-strip">'
        '<span class="glyph">ॐ</span>'
        f'<div class="text">{escape(message)}</div>'
        "</div>"
    )


def divider_ornament(glyph: str = "॥ ॐ ॥") -> None:
    """Render a manuscript-style divider with optional glyph."""
    _emit('<div class="divider-ornament">' f'<span class="glyph">{escape(glyph)}</span>' "</div>")


def sidebar_brand() -> None:
    """Render the brand mark in the sidebar."""
    _emit(
        '<div class="brand-row">'
        '<div class="brand-mark">ॐ</div>'
        "<div>"
        '<div class="brand-name">OCR Devnagari</div>'
        '<div class="brand-sub">v0.1 · ui-work</div>'
        "</div>"
        "</div>"
    )


def sidebar_session_card(*, project: str, auth: str, spend_today: str) -> None:
    """Render the session-info footer at the bottom of the sidebar."""
    _emit(
        '<div class="sidebar-foot">'
        f'<div class="row"><span>Auth</span><span class="val">{escape(auth)}</span></div>'
        f'<div class="row"><span>Project</span><span class="val">{escape(project)}</span></div>'
        f'<div class="row"><span>Spend today</span><span class="val">{escape(spend_today)}</span></div>'
        "</div>"
    )


def deva_block(text: str) -> None:
    """Render Devanagari text in the manuscript-styled block.

    Splits paragraphs on blank lines, treats lines beginning with `||` or
    `॥` as centred sacred lines.
    """
    parts: list[str] = ['<div class="deva-block">']
    for raw_para in text.split("\n\n"):
        para = raw_para.strip()
        if not para:
            continue
        is_centred = para.startswith("॥") or para.startswith("||") or para.startswith("ॐ")
        klass = ' class="center"' if is_centred else ""
        parts.append(f"<p{klass}>{escape(para)}</p>")
    parts.append("</div>")
    _emit("".join(parts))


def log_stream(lines: Iterable[tuple[str, str, str]]) -> None:
    """Render a terminal-style log stream.

    Each line is (timestamp, level, message). Level is one of
    INFO, WARN, ERROR, MANTRA, OCR.
    """
    rows = []
    for ts, lvl, msg in lines:
        lvl_clean = lvl.upper().strip()[:6].ljust(6)
        rows.append(
            f'<div><span class="ts">{escape(ts)}</span> '
            f'<span class="lvl-{escape(lvl_clean.strip())}">{escape(lvl_clean)}</span> '
            f"{escape(msg)}</div>"
        )
    _emit(f'<div class="log-stream">{"".join(rows)}</div>')


def atlas_grid(cells: Iterable[str]) -> None:
    """Render the page-status atlas grid.

    Each cell is one of: easyocr, gemini, mantra, failed, active, pending.
    """
    cell_html = "".join(f'<div class="cell {escape(c)}"></div>' for c in cells)
    _emit(f'<div class="atlas">{cell_html}</div>')


def engine_card(
    *,
    name: str,
    deva: str,
    tag: str,
    tag_kind: str,
    description: str,
    cost: str,
    accuracy: str,
    speed: str,
    flag: str,
    strengths: list[str],
    featured: bool = False,
) -> None:
    """Render a single engine card with stats and strengths."""
    feat_class = "featured" if featured else ""
    feat_pill = '<div class="featured-pill">★ DEFAULT</div>' if featured else ""
    cost_class = "value free" if cost.strip() in {"$0.00", "FREE", "free"} else "value"
    strengths_html = "".join(
        '<div style="display:flex;gap:6px;font-size:12px;color:var(--ink-700);align-items:center">'
        f'<span style="color:var(--saffron-500)">✓</span>{escape(s)}</div>'
        for s in strengths
    )
    _emit(
        f'<div class="engine-card {feat_class}">'
        f"{feat_pill}"
        '<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px;">'
        "<div>"
        f'<div class="engine-name">{escape(name)}</div>'
        f'<div class="engine-deva">{escape(deva)}</div>'
        "</div>"
        f'<span class="badge badge-{escape(tag_kind)}">{escape(tag)}</span>'
        "</div>"
        f'<p class="engine-desc">{escape(description)}</p>'
        '<div style="display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-bottom:14px;">'
        f'<div class="engine-stat"><div class="label">COST/1K</div><div class="{cost_class}">{escape(cost)}</div></div>'
        f'<div class="engine-stat"><div class="label">ACCURACY</div><div class="value">{escape(accuracy)}</div></div>'
        f'<div class="engine-stat"><div class="label">PPM</div><div class="value">{escape(speed)}</div></div>'
        "</div>"
        '<div style="display:flex;flex-direction:column;gap:6px;margin-bottom:14px;">'
        f"{strengths_html}"
        "</div>"
        '<div style="display:flex;justify-content:space-between;align-items:center;padding-top:10px;border-top:1px solid var(--surface-alt);">'
        f'<span class="mono" style="font-size:11px;color:var(--ink-400);">{escape(flag)}</span>'
        "</div>"
        "</div>"
    )


def estimate_footer(
    *,
    cost: str,
    cost_delta: str,
    time_estimate: str,
    pages_per_min: str,
    output_path: str,
    cache_path: str,
) -> None:
    """Render the bottom estimate panel on the Configure screen."""
    _emit(
        '<div style="margin-top:24px;background:linear-gradient(180deg, var(--card) 0%, var(--surface) 100%);'
        "border:1px solid var(--border);border-radius:12px;padding:20px 28px;"
        'display:grid;grid-template-columns:1fr 1fr 2fr;gap:32px;align-items:center;">'
        "<div>"
        '<div class="stat-label">Estimated cost</div>'
        f'<div class="stat-value" style="color:var(--maroon-700);">{escape(cost)}</div>'
        f'<div class="stat-delta">{escape(cost_delta)}</div>'
        "</div>"
        "<div>"
        '<div class="stat-label">Estimated time</div>'
        f'<div class="stat-value">{escape(time_estimate)}</div>'
        f'<div class="stat-delta" style="color:var(--ink-500);">{escape(pages_per_min)}</div>'
        "</div>"
        "<div>"
        '<div class="stat-label">Output</div>'
        '<div style="font-family:var(--font-mono);font-size:13px;color:var(--ink-700);margin-top:6px;line-height:1.5;">'
        f"{escape(output_path)}<br>"
        f'<span style="color:var(--ink-400);font-size:11px;">+ {escape(cache_path)}</span>'
        "</div>"
        "</div>"
        "</div>"
    )


def tweaks_panel() -> tuple[str, str]:
    """Render the theme + Devanagari font tweaks in the sidebar."""
    _emit(
        '<div style="font-family:var(--font-mono);font-size:10px;letter-spacing:0.10em;'
        'text-transform:uppercase;color:var(--ink-400);margin:12px 0 6px;">TWEAKS</div>'
    )
    theme_choice = st.selectbox(
        "Theme",
        list(theme.THEMES.keys()),
        index=list(theme.THEMES.keys()).index(st.session_state.get("theme", "Parchment")),
        key="_theme_select",
    )
    deva_choice = st.selectbox(
        "Devanagari font",
        list(theme.DEVA_FONTS.keys()),
        index=list(theme.DEVA_FONTS.keys()).index(
            st.session_state.get("deva_font", "Noto Serif Devanagari")
        ),
        key="_deva_select",
    )
    if theme_choice != st.session_state.get("theme") or deva_choice != st.session_state.get(
        "deva_font"
    ):
        st.session_state["theme"] = theme_choice
        st.session_state["deva_font"] = deva_choice
        st.rerun()
    return theme_choice, deva_choice
