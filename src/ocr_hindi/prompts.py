"""
OCR Prompts optimized for Hindi/Sanskrit Tantric texts
"""

OCR_PROMPT = """Extract ALL text from this scanned page in proper Unicode Devanagari.

CRITICAL RULES:
1. Output ONLY the extracted text - no explanations, headers, or metadata
2. Preserve exact verse/shloka numbering (॥१॥, ॥२॥, etc.)
3. Preserve section headings and chapter markers
4. Maintain paragraph breaks and structure
5. For Sanskrit verses: keep the original line breaks
6. If text is unclear, make best effort - do not skip

This is a tantric/spiritual text - preserve all mantras and technical terms exactly."""

OCR_PROMPT_DETAILED = """You are an expert OCR system for Sanskrit and Hindi manuscripts.

Extract ALL text from this scanned page following these rules:

OUTPUT FORMAT:
- Output ONLY the extracted Devanagari text
- No explanations, no "Here is the text:", no metadata
- Start directly with the first word of the text

PRESERVATION RULES:
1. VERSE NUMBERING: Keep exact format (॥१॥, ॥२॥, ||1||, etc.)
2. SECTION MARKERS: Preserve chapter headers, section titles
3. LINE BREAKS: Maintain verse line structure
4. PUNCTUATION: Keep all daṇḍa (।) and double daṇḍa (॥)
5. SPECIAL CHARACTERS: Preserve anusvāra (ं), visarga (ः), chandrabindu (ँ)

HANDLING UNCLEAR TEXT:
- Make best effort based on context
- Never leave gaps or [illegible] markers
- Use surrounding words to infer unclear portions

TEXT TYPE: Tantric/spiritual manuscript with mantras and technical terminology.
Accuracy of mantras is critical - preserve exact spelling."""

# Simpler prompt for faster processing
OCR_PROMPT_FAST = """Extract all Devanagari text from this page exactly as written.
Keep verse numbers (॥१॥), punctuation (।॥), and line breaks.
Output only the text, nothing else."""
