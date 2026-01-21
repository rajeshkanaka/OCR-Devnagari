"""
Mantra detection for selective LLM verification.

Detects patterns that indicate mantras, yantras, and critical Sanskrit text
that requires higher accuracy verification.
"""

import re
from dataclasses import dataclass
from typing import Optional


@dataclass
class MantraDetectionResult:
    """Result of mantra detection"""
    contains_mantra: bool
    confidence: float  # How confident we are that this is a mantra section
    patterns_found: list[str]
    mantra_count: int
    recommendation: str  # "verify", "skip", "high_priority"


class MantraDetector:
    """
    Detects mantras and critical Sanskrit patterns in text.
    
    Used by the hybrid backend to decide which pages need
    Gemini verification for accuracy.
    """
    
    # Bija mantras (seed syllables) - critical accuracy
    BIJA_MANTRAS = [
        "ॐ", "ओं",  # Om
        "ह्रीं", "हृीं",  # Hrim
        "श्रीं", "श्री",  # Shrim
        "क्लीं", "क्ली",  # Klim
        "ऐं",  # Aim
        "हुं", "हूं",  # Hum
        "फट्", "फट",  # Phat
        "स्वाहा",  # Swaha
        "नमः", "नम:",  # Namah
        "वौषट्",  # Vaushat
        "वषट्",  # Vashat
        "हं", "हाँ",  # Ham
        "क्षं",  # Ksham
        "ठः",  # Thah
        "क्रों", "क्रौं",  # Kraum
        "ग्लौं",  # Glaum
        "द्रां", "द्रीं", "द्रूं",  # Dram, Drim, Drum
        "ब्लूं",  # Blum
        "स्त्रीं",  # Strim
    ]
    
    # Verse/shloka markers
    VERSE_MARKERS = [
        "॥",  # Double danda (verse end)
        "।।",  # Alternative double danda
        "||",  # ASCII double danda
    ]
    
    # Mantra section indicators
    SECTION_INDICATORS = [
        "मन्त्र", "मंत्र",  # Mantra
        "यन्त्र", "यंत्र",  # Yantra
        "तन्त्र", "तंत्र",  # Tantra
        "विनियोग",  # Viniyoga (mantra application)
        "ऋषि",  # Rishi (seer)
        "छन्द", "छंद",  # Chanda (meter)
        "देवता",  # Devata (deity)
        "बीज",  # Bija (seed)
        "शक्ति",  # Shakti (power)
        "कीलक",  # Kilaka (key)
        "न्यास",  # Nyasa (placement)
        "ध्यान",  # Dhyana (meditation)
        "कवच",  # Kavacha (armor/protection)
        "स्तोत्र",  # Stotra (hymn)
        "सूक्त",  # Sukta (hymn)
        "जप",  # Japa (repetition)
        "पुरश्चरण",  # Purascharana (preliminary practice)
        "अनुष्ठान",  # Anushthana (practice)
        "साधना",  # Sadhana (spiritual practice)
        "दीक्षा",  # Diksha (initiation)
        "होम", "हवन",  # Homa/Havana (fire ritual)
        "आहुति",  # Ahuti (offering)
        "प्राणप्रतिष्ठा",  # Prana pratishtha (life installation)
    ]
    
    # Deity names (often part of mantras)
    DEITY_NAMES = [
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
    ]
    
    # Yantra-related terms
    YANTRA_TERMS = [
        "यन्त्र", "यंत्र",
        "मण्डल", "मंडल",
        "चक्र",
        "त्रिकोण",  # Triangle
        "षट्कोण",  # Hexagon
        "अष्टदल",  # Eight petals
        "बिन्दु", "बिंदु",  # Point
        "भूपुर",  # Frame
        "कमल",  # Lotus
        "पद्म",  # Lotus
        "श्रीचक्र",  # Sri Chakra
        "श्रीयन्त्र",  # Sri Yantra
    ]
    
    # Numbered verse patterns (e.g., ॥१॥, ॥२॥)
    VERSE_NUMBER_PATTERN = re.compile(r'॥\s*\d+\s*॥|॥\s*[०-९]+\s*॥|\|\|\s*\d+\s*\|\|')
    
    def __init__(self, strict_mode: bool = True):
        """
        Initialize detector.
        
        Args:
            strict_mode: If True, any mantra pattern triggers verification.
                        If False, require multiple patterns.
        """
        self.strict_mode = strict_mode
    
    def detect(self, text: str) -> MantraDetectionResult:
        """
        Detect mantra patterns in text.
        
        Args:
            text: Text to analyze
        
        Returns:
            MantraDetectionResult with detection details
        """
        if not text:
            return MantraDetectionResult(
                contains_mantra=False,
                confidence=0.0,
                patterns_found=[],
                mantra_count=0,
                recommendation="skip",
            )
        
        patterns_found = []
        scores = []
        
        # Check for bija mantras (highest priority)
        bija_count = 0
        for bija in self.BIJA_MANTRAS:
            count = text.count(bija)
            if count > 0:
                bija_count += count
                patterns_found.append(f"bija:{bija}x{count}")
                scores.append(0.9)  # High confidence
        
        # Check for verse markers
        verse_marker_count = sum(text.count(m) for m in self.VERSE_MARKERS)
        if verse_marker_count > 0:
            patterns_found.append(f"verse_markers:{verse_marker_count}")
            scores.append(0.7)
        
        # Check for numbered verses
        numbered_verses = len(self.VERSE_NUMBER_PATTERN.findall(text))
        if numbered_verses > 0:
            patterns_found.append(f"numbered_verses:{numbered_verses}")
            scores.append(0.8)
        
        # Check for section indicators
        section_count = 0
        for indicator in self.SECTION_INDICATORS:
            if indicator in text:
                section_count += 1
                if len(patterns_found) < 10:  # Limit for readability
                    patterns_found.append(f"section:{indicator}")
        if section_count > 0:
            scores.append(min(0.85, 0.5 + section_count * 0.1))
        
        # Check for deity names
        deity_count = 0
        for deity in self.DEITY_NAMES:
            if deity in text:
                deity_count += 1
        if deity_count > 0:
            patterns_found.append(f"deities:{deity_count}")
            scores.append(0.6)
        
        # Check for yantra terms
        yantra_count = 0
        for term in self.YANTRA_TERMS:
            if term in text:
                yantra_count += 1
        if yantra_count > 0:
            patterns_found.append(f"yantra_terms:{yantra_count}")
            scores.append(0.75)
        
        # Calculate overall confidence
        if not scores:
            confidence = 0.0
        else:
            # Weight by max score but also consider count
            confidence = max(scores) * (1 + min(len(scores) - 1, 5) * 0.05)
            confidence = min(1.0, confidence)
        
        # Determine if contains mantra
        mantra_count = bija_count + numbered_verses
        
        if self.strict_mode:
            contains_mantra = bija_count > 0 or numbered_verses > 0 or section_count >= 2
        else:
            contains_mantra = (
                bija_count >= 2 or 
                (numbered_verses > 0 and section_count > 0) or
                confidence > 0.8
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
        """
        Quick check if text needs LLM verification.
        
        Args:
            text: Text to check
        
        Returns:
            True if verification recommended
        """
        result = self.detect(text)
        return result.recommendation in ("verify", "high_priority")
    
    def get_priority_score(self, text: str) -> float:
        """
        Get verification priority score (0-1).
        Higher means more important to verify.
        
        Args:
            text: Text to analyze
        
        Returns:
            Priority score (0.0 to 1.0)
        """
        result = self.detect(text)
        
        if result.recommendation == "high_priority":
            return 1.0
        elif result.recommendation == "verify":
            return 0.5 + result.confidence * 0.4
        else:
            return result.confidence * 0.3


# Convenience function
def detect_mantras(text: str, strict: bool = True) -> MantraDetectionResult:
    """
    Detect mantras in text.
    
    Args:
        text: Text to analyze
        strict: Use strict detection mode
    
    Returns:
        MantraDetectionResult
    """
    detector = MantraDetector(strict_mode=strict)
    return detector.detect(text)
