"""Mantra detection for selective LLM verification.

Detects patterns that indicate mantras, yantras, and critical Sanskrit text
that requires higher accuracy verification.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class MantraDetectionResult:
    """Result of mantra detection."""

    contains_mantra: bool
    confidence: float
    patterns_found: list[str] = field(default_factory=list)
    mantra_count: int = 0
    recommendation: str = "skip"  # "verify", "skip", "high_priority"


class MantraDetector:
    """Detects mantras and critical Sanskrit patterns in text.

    Used by the hybrid backend to decide which pages need
    Gemini verification for accuracy.
    """

    # Bija mantras (seed syllables) - critical accuracy
    BIJA_MANTRAS = (
        "ॐ", "ओं",
        "ह्रीं", "हृीं",
        "श्रीं", "श्री",
        "क्लीं", "क्ली",
        "ऐं",
        "हुं", "हूं",
        "फट्", "फट",
        "स्वाहा",
        "नमः", "नम:",
        "वौषट्",
        "वषट्",
        "हं", "हाँ",
        "क्षं",
        "ठः",
        "क्रों", "क्रौं",
        "ग्लौं",
        "द्रां", "द्रीं", "द्रूं",
        "ब्लूं",
        "स्त्रीं",
    )

    # Verse/shloka markers
    VERSE_MARKERS = ("॥", "।।", "||")

    # Mantra section indicators
    SECTION_INDICATORS = (
        "मन्त्र", "मंत्र",
        "यन्त्र", "यंत्र",
        "तन्त्र", "तंत्र",
        "विनियोग",
        "ऋषि",
        "छन्द", "छंद",
        "देवता",
        "बीज",
        "शक्ति",
        "कीलक",
        "न्यास",
        "ध्यान",
        "कवच",
        "स्तोत्र",
        "सूक्त",
        "जप",
        "पुरश्चरण",
        "अनुष्ठान",
        "साधना",
        "दीक्षा",
        "होम", "हवन",
        "आहुति",
        "प्राणप्रतिष्ठा",
    )

    # Deity names (often part of mantras)
    DEITY_NAMES = (
        "शिव", "महादेव", "रुद्र",
        "विष्णु", "नारायण", "हरि",
        "ब्रह्मा",
        "गणेश", "गणपति", "विनायक",
        "दुर्गा", "काली", "चण्डी", "चामुण्डा",
        "लक्ष्मी", "सरस्वती",
        "हनुमान", "मारुति",
        "सूर्य", "चन्द्र",
        "भैरव", "भैरवी",
        "त्रिपुरसुन्दरी", "ललिता", "राजराजेश्वरी",
        "तारा", "बगलामुखी", "धूमावती",
        "मातङ्गी", "कमला",
    )

    # Yantra-related terms
    YANTRA_TERMS = (
        "यन्त्र", "यंत्र",
        "मण्डल", "मंडल",
        "चक्र",
        "त्रिकोण",
        "षट्कोण",
        "अष्टदल",
        "बिन्दु", "बिंदु",
        "भूपुर",
        "कमल",
        "पद्म",
        "श्रीचक्र",
        "श्रीयन्त्र",
    )

    # Numbered verse patterns (e.g., ॥१॥, ॥२॥)
    _VERSE_NUMBER_RE = re.compile(
        r"॥\s*\d+\s*॥|॥\s*[०-९]+\s*॥|\|\|\s*\d+\s*\|\|"
    )

    def __init__(self, strict_mode: bool = True) -> None:
        """Initialize detector.

        Args:
            strict_mode: If True, any mantra pattern triggers verification.
                        If False, require multiple patterns.
        """
        self.strict_mode = strict_mode

    def detect(self, text: str) -> MantraDetectionResult:
        """Detect mantra patterns in text.

        Args:
            text: Text to analyze.

        Returns:
            MantraDetectionResult with detection details.
        """
        if not text:
            return MantraDetectionResult(
                contains_mantra=False,
                confidence=0.0,
            )

        patterns_found: list[str] = []
        scores: list[float] = []

        # Check for bija mantras (highest priority)
        bija_count = 0
        for bija in self.BIJA_MANTRAS:
            count = text.count(bija)
            if count > 0:
                bija_count += count
                patterns_found.append(f"bija:{bija}x{count}")
                scores.append(0.9)

        # Check for verse markers
        verse_marker_count = sum(text.count(m) for m in self.VERSE_MARKERS)
        if verse_marker_count > 0:
            patterns_found.append(f"verse_markers:{verse_marker_count}")
            scores.append(0.7)

        # Check for numbered verses
        numbered_verses = len(self._VERSE_NUMBER_RE.findall(text))
        if numbered_verses > 0:
            patterns_found.append(f"numbered_verses:{numbered_verses}")
            scores.append(0.8)

        # Check for section indicators
        section_count = 0
        for indicator in self.SECTION_INDICATORS:
            if indicator in text:
                section_count += 1
                if len(patterns_found) < 10:
                    patterns_found.append(f"section:{indicator}")
        if section_count > 0:
            scores.append(min(0.85, 0.5 + section_count * 0.1))

        # Check for deity names
        deity_count = sum(1 for deity in self.DEITY_NAMES if deity in text)
        if deity_count > 0:
            patterns_found.append(f"deities:{deity_count}")
            scores.append(0.6)

        # Check for yantra terms
        yantra_count = sum(1 for term in self.YANTRA_TERMS if term in text)
        if yantra_count > 0:
            patterns_found.append(f"yantra_terms:{yantra_count}")
            scores.append(0.75)

        # Calculate overall confidence
        if not scores:
            confidence = 0.0
        else:
            confidence = max(scores) * (1 + min(len(scores) - 1, 5) * 0.05)
            confidence = min(1.0, confidence)

        mantra_count = bija_count + numbered_verses

        if self.strict_mode:
            contains_mantra = (
                bija_count > 0 or numbered_verses > 0 or section_count >= 2
            )
        else:
            contains_mantra = (
                bija_count >= 2
                or (numbered_verses > 0 and section_count > 0)
                or confidence > 0.8
            )

        # Determine recommendation
        if bija_count >= 3 or (bija_count > 0 and section_count >= 2):
            recommendation = "high_priority"
        elif contains_mantra:
            recommendation = "verify"
        else:
            recommendation = "skip"

        return MantraDetectionResult(
            contains_mantra=contains_mantra,
            confidence=confidence,
            patterns_found=patterns_found,
            mantra_count=mantra_count,
            recommendation=recommendation,
        )

    def needs_verification(self, text: str) -> bool:
        """Quick check if text needs LLM verification.

        Args:
            text: Text to check.

        Returns:
            True if verification recommended.
        """
        result = self.detect(text)
        return result.recommendation in ("verify", "high_priority")

    def get_priority_score(self, text: str) -> float:
        """Get verification priority score (0-1).

        Higher means more important to verify.

        Args:
            text: Text to analyze.

        Returns:
            Priority score (0.0 to 1.0).
        """
        result = self.detect(text)

        if result.recommendation == "high_priority":
            return 1.0
        if result.recommendation == "verify":
            return 0.5 + result.confidence * 0.4
        return result.confidence * 0.3


def detect_mantras(text: str, *, strict: bool = True) -> MantraDetectionResult:
    """Detect mantras in text (convenience function).

    Args:
        text: Text to analyze.
        strict: Use strict detection mode.

    Returns:
        MantraDetectionResult.
    """
    detector = MantraDetector(strict_mode=strict)
    return detector.detect(text)
