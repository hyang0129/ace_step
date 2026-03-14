"""Map free-text mood/tone keywords to the best-matching preset.

Used by video_agent's MusicAgent to translate script tone metadata
into an ace_step preset ID for music generation.
"""

from __future__ import annotations

from ace_step.models import PresetInfo
from ace_step.presets import get_preset, list_presets

# Keyword → preset ID mapping.  Each keyword list is checked with simple
# substring matching against a caller-provided tone string.
_MOOD_KEYWORDS: dict[str, list[str]] = {
    "documentary_ambient": [
        "ambient", "atmospheric", "reflective", "calm", "meditative",
        "contemplative", "documentary", "neutral",
    ],
    "history_epic": [
        "epic", "grand", "historical", "dramatic", "cinematic",
        "powerful", "heroic", "majestic",
    ],
    "biography_warm": [
        "warm", "intimate", "nostalgic", "personal", "biographical",
        "hopeful", "gentle", "heartfelt",
    ],
    "science_curiosity": [
        "curious", "playful", "educational", "science", "tech",
        "modern", "quirky", "discovery",
    ],
    "investigation_tension": [
        "tense", "suspenseful", "dark", "mystery", "investigation",
        "thriller", "ominous", "eerie",
    ],
    "travel_upbeat": [
        "upbeat", "cheerful", "adventure", "travel", "energetic",
        "positive", "fun", "lively",
    ],
    "economics_neutral": [
        "corporate", "business", "economics", "news", "neutral",
        "professional", "minimal", "clean",
    ],
    "nature_peaceful": [
        "peaceful", "nature", "serene", "pastoral", "organic",
        "relaxing", "tranquil", "soothing",
    ],
}

# Default when no keywords match.
_DEFAULT_PRESET_ID = "documentary_ambient"


def match_preset(tone: str) -> PresetInfo:
    """Return the preset that best matches a free-text *tone* string.

    Matching is case-insensitive substring search.  The preset with the
    most keyword hits wins.  Ties are broken by declaration order.
    Falls back to ``documentary_ambient`` if nothing matches.
    """
    tone_lower = tone.lower()
    best_id = _DEFAULT_PRESET_ID
    best_score = 0
    for preset_id, keywords in _MOOD_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in tone_lower)
        if score > best_score:
            best_score = score
            best_id = preset_id
    preset = get_preset(best_id)
    assert preset is not None
    return preset
