"""Tests for app.presets — built-in documentary music presets."""

from __future__ import annotations

from app.presets import get_preset, list_presets


class TestGetPreset:
    def test_known_preset(self):
        p = get_preset("documentary_ambient")
        assert p is not None
        assert p.id == "documentary_ambient"
        assert "ambient" in p.description.lower()
        assert p.bpm is not None

    def test_all_known_ids(self):
        known = [
            "documentary_ambient",
            "history_epic",
            "biography_warm",
            "science_curiosity",
            "investigation_tension",
            "travel_upbeat",
            "economics_neutral",
            "nature_peaceful",
        ]
        for pid in known:
            assert get_preset(pid) is not None, f"Missing preset: {pid}"

    def test_unknown_preset(self):
        assert get_preset("nonexistent_xyz") is None


class TestListPresets:
    def test_returns_all(self):
        presets = list_presets()
        assert len(presets) == 8

    def test_sorted_by_id(self):
        presets = list_presets()
        ids = [p.id for p in presets]
        assert ids == sorted(ids)

    def test_all_have_description(self):
        for p in list_presets():
            assert p.description, f"Preset {p.id} has empty description"

    def test_all_have_tags(self):
        for p in list_presets():
            assert len(p.tags) > 0, f"Preset {p.id} has no tags"

    def test_all_instrumental_defaults(self):
        """Presets are for documentary background music — no vocal params."""
        for p in list_presets():
            assert p.duration >= 10
            assert p.guidance_scale >= 1.0
