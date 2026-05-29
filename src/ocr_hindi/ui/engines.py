"""Static engine metadata for the UI.

This data is presented in the Configure and Engines screens. The
runtime engine list is still driven by `_BACKEND_MAP` in
`ocr_hindi.backends`; this module only adds presentation extras
(Devanagari label, accuracy/speed, strengths, descriptions).
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EngineInfo:
    id: str
    name: str
    deva: str
    tag: str
    tag_kind: str
    cost: str
    cost_per_1k: float
    accuracy: int
    speed_ppm: int
    ram: str
    description: str
    flag: str
    strengths: list[str] = field(default_factory=list)
    featured: bool = False


# Order matches what the user expects to see in the picker
ENGINES: list[EngineInfo] = [
    EngineInfo(
        id="hybrid",
        name="Hybrid",
        deva="मिश्र",
        tag="RECOMMENDED",
        tag_kind="saffron",
        cost="~$0.10",
        cost_per_1k=0.10,
        accuracy=95,
        speed_ppm=11,
        ram="2 GB",
        description=(
            "EasyOCR runs first; pages below confidence threshold or detected "
            "as mantras escalate to Gemini 2.0 Flash."
        ),
        flag="-e hybrid",
        featured=True,
        strengths=["Best cost/accuracy", "Mantra-aware routing", "Survives 1000+ pages"],
    ),
    EngineInfo(
        id="easyocr",
        name="EasyOCR",
        deva="स्थानीय",
        tag="FREE",
        tag_kind="sage",
        cost="$0.00",
        cost_per_1k=0.0,
        accuracy=84,
        speed_ppm=8,
        ram="1.5 GB",
        description=(
            "Local PyTorch OCR with Hindi/Devanagari support. "
            "No API calls, runs entirely on your machine."
        ),
        flag="-e easyocr",
        strengths=["100% offline", "No setup", "Predictable speed"],
    ),
    EngineInfo(
        id="marker",
        name="Marker",
        deva="ग्रन्थ",
        tag="FREE",
        tag_kind="sage",
        cost="$0.00",
        cost_per_1k=0.0,
        accuracy=92,
        speed_ppm=16,
        ram="3 GB",
        description=(
            "Best for structured printed books. Native markdown output, "
            "preserves headings and lists."
        ),
        flag="-e marker",
        strengths=["Best for books", "Markdown output", "Layout aware"],
    ),
    EngineInfo(
        id="chandra",
        name="Chandra",
        deva="विद्या",
        tag="FREE · VLM",
        tag_kind="sage",
        cost="$0.00",
        cost_per_1k=0.0,
        accuracy=91,
        speed_ppm=6,
        ram="8 GB",
        description=(
            "Vision-language model for structured documents with tables and " "complex layout."
        ),
        flag="-e chandra",
        strengths=["Tables & layout", "Modern VLM", "Local inference"],
    ),
    EngineInfo(
        id="tesseract",
        name="Tesseract",
        deva="मूल",
        tag="FREE",
        tag_kind="sage",
        cost="$0.00",
        cost_per_1k=0.0,
        accuracy=71,
        speed_ppm=22,
        ram="200 MB",
        description=(
            "Classic OCR. Fast and lightweight, but struggles with conjuncts " "and ornate scripts."
        ),
        flag="-e tesseract",
        strengths=["Fastest", "Lightest", "Universally available"],
    ),
    EngineInfo(
        id="gemini",
        name="Gemini",
        deva="रत्न",
        tag="PREMIUM",
        tag_kind="maroon",
        cost="~$2.00",
        cost_per_1k=2.0,
        accuracy=97,
        speed_ppm=22,
        ram="—",
        description=(
            "Pure Gemini 2.0 Flash with high media resolution. Highest " "accuracy, highest cost."
        ),
        flag="-e gemini",
        strengths=["Maximum accuracy", "Handles damage", "Reads margins"],
    ),
]


ENGINES_BY_ID: dict[str, EngineInfo] = {e.id: e for e in ENGINES}


def estimate_cost(engine_id: str, num_pages: int) -> float:
    """Estimate cost in USD for processing `num_pages` with `engine_id`."""
    e = ENGINES_BY_ID.get(engine_id)
    if not e or num_pages <= 0:
        return 0.0
    return (e.cost_per_1k / 1000.0) * num_pages


def estimate_minutes(engine_id: str, num_pages: int, workers: int) -> float:
    """Rough time estimate in minutes."""
    e = ENGINES_BY_ID.get(engine_id)
    if not e or num_pages <= 0:
        return 0.0
    effective_ppm = e.speed_ppm * max(1, min(workers, 8) / 4)
    return num_pages / max(effective_ppm, 1.0)
