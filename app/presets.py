"""Built-in music presets for documentary / educational video content.

Each preset maps to a curated ACE-Step caption plus sensible defaults for
BPM, duration, guidance scale, etc.  The video_agent can reference a preset
by ID instead of crafting a raw description every time.
"""

from __future__ import annotations

from app.models import PresetInfo

_PRESETS: dict[str, PresetInfo] = {
    # --- ambient / atmospheric -------------------------------------------
    "documentary_ambient": PresetInfo(
        id="documentary_ambient",
        name="Documentary Ambient",
        description=(
            "ambient, atmospheric, soft pads, gentle piano, minimal percussion, "
            "documentary background, reflective, cinematic"
        ),
        tags=["ambient", "documentary", "reflective"],
        duration=60,
        bpm=80,
        guidance_scale=7.0,
    ),
    "history_epic": PresetInfo(
        id="history_epic",
        name="History Epic",
        description=(
            "orchestral, epic, strings, brass, timpani, cinematic, historical, "
            "grand, inspiring, documentary score"
        ),
        tags=["orchestral", "epic", "history"],
        duration=60,
        bpm=100,
        guidance_scale=8.0,
    ),
    "biography_warm": PresetInfo(
        id="biography_warm",
        name="Biography Warm",
        description=(
            "warm piano, gentle strings, acoustic guitar, intimate, biographical, "
            "nostalgic, hopeful, documentary"
        ),
        tags=["piano", "warm", "biography"],
        duration=45,
        bpm=90,
        guidance_scale=7.0,
    ),
    "science_curiosity": PresetInfo(
        id="science_curiosity",
        name="Science & Curiosity",
        description=(
            "electronic, plucky synths, light percussion, curious, playful, "
            "science documentary, educational, modern"
        ),
        tags=["electronic", "science", "curious"],
        duration=30,
        bpm=110,
        guidance_scale=7.5,
    ),
    "investigation_tension": PresetInfo(
        id="investigation_tension",
        name="Investigation Tension",
        description=(
            "dark ambient, low drone, subtle percussion, suspenseful, tense, "
            "investigative documentary, mystery"
        ),
        tags=["dark", "suspense", "investigation"],
        duration=45,
        bpm=70,
        key="D minor",
        guidance_scale=8.0,
    ),
    "travel_upbeat": PresetInfo(
        id="travel_upbeat",
        name="Travel Upbeat",
        description=(
            "upbeat, acoustic guitar, light drums, marimba, cheerful, travel "
            "documentary, adventure, positive energy"
        ),
        tags=["upbeat", "travel", "adventure"],
        duration=30,
        bpm=120,
        guidance_scale=7.0,
    ),
    "economics_neutral": PresetInfo(
        id="economics_neutral",
        name="Economics Neutral",
        description=(
            "minimal, clean piano, soft synth pads, neutral tone, corporate, "
            "economics explainer, news background, modern"
        ),
        tags=["minimal", "corporate", "economics"],
        duration=45,
        bpm=95,
        guidance_scale=6.5,
    ),
    "nature_peaceful": PresetInfo(
        id="nature_peaceful",
        name="Nature Peaceful",
        description=(
            "peaceful, flowing strings, flute, harp, nature documentary, serene, "
            "pastoral, gentle, organic"
        ),
        tags=["nature", "peaceful", "pastoral"],
        duration=60,
        bpm=75,
        key="G Major",
        guidance_scale=7.0,
    ),
}


def get_preset(preset_id: str) -> PresetInfo | None:
    """Return a preset by ID, or *None* if it does not exist."""
    return _PRESETS.get(preset_id)


def list_presets() -> list[PresetInfo]:
    """Return all available presets sorted by ID."""
    return sorted(_PRESETS.values(), key=lambda p: p.id)
