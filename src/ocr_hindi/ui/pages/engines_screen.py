"""Screen 2 — Engine Picker.

Cost-vs-accuracy scatter plot + 6 engine cards from `engines.ENGINES`.
"""

from __future__ import annotations

import streamlit as st

from ocr_hindi.ui import components, engines
from ocr_hindi.ui.layout import setup_page, sidebar_footer


def _scatter_plot() -> None:
    """Render a small inline matplotlib chart of cost vs accuracy."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        st.info("Install matplotlib to view the cost-vs-accuracy plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 3.2), dpi=110)
    fig.patch.set_facecolor("#fffaf0")
    ax.set_facecolor("#fffaf0")

    for engine in engines.ENGINES:
        color = (
            "#c8551d"
            if engine.id == "hybrid"
            else "#6b2410"
            if engine.id == "gemini"
            else "#4a6b3e"
        )
        ax.scatter(
            engine.cost_per_1k,
            engine.accuracy,
            s=180 if engine.featured else 110,
            c=color,
            edgecolors="white",
            linewidths=2,
            zorder=3,
        )
        ax.annotate(
            f"  {engine.name}",
            (engine.cost_per_1k, engine.accuracy),
            fontsize=9,
            color="#1a1410",
            fontweight="bold",
            xytext=(8, 0),
            textcoords="offset points",
            va="center",
        )

    ax.set_xlim(-0.15, 2.4)
    ax.set_ylim(65, 100)
    ax.set_xlabel("Cost per 1K pages (USD)", color="#6b5642", fontsize=10)
    ax.set_ylabel("Accuracy %", color="#6b5642", fontsize=10)
    ax.grid(True, color="#ecdfc1", linestyle="-", linewidth=0.6, zorder=1)
    for spine in ax.spines.values():
        spine.set_color("#ddc89a")
    ax.tick_params(colors="#8a755e", labelsize=9)
    fig.tight_layout()
    st.pyplot(fig, use_container_width=True)


def render() -> None:
    setup_page("Engines")
    components.page_header(
        crumbs=["Workflow", "Engines"],
        title="Six engines, one pipeline",
        sub=(
            "Each backend is a swappable module behind a common OCRBackend "
            "interface. Compare cost, accuracy, and fit before you commit a "
            "1,000-page run."
        ),
    )

    components.card_open(
        "Cost vs accuracy",
        "on 1,000 pages of mixed Devanagari manuscript · benchmarked locally",
    )
    _scatter_plot()
    components.card_close()

    cols = st.columns(3)
    for i, engine in enumerate(engines.ENGINES):
        with cols[i % 3]:
            components.engine_card(
                name=engine.name,
                deva=engine.deva,
                tag=engine.tag,
                tag_kind=engine.tag_kind,
                description=engine.description,
                cost=engine.cost,
                accuracy=f"{engine.accuracy}%",
                speed=str(engine.speed_ppm),
                flag=engine.flag,
                strengths=engine.strengths,
                featured=engine.featured,
            )
            picked = st.button(
                "Use this" if engine.featured else "Select",
                key=f"pick_{engine.id}",
                type="primary" if engine.featured else "secondary",
                use_container_width=True,
            )
            if picked:
                st.session_state["engine"] = engine.id
                st.toast(f"{engine.name} selected · open Configure & Run", icon="✓")

    sidebar_footer()


if __name__ == "__main__":
    render()
