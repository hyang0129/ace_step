"""Tests for app.models — shared types."""

from __future__ import annotations

from ace_step.models import PresetInfo


class TestPresetInfo:
    def test_defaults(self):
        p = PresetInfo(id="test", name="Test", description="test desc")
        assert p.tags == []
        assert p.duration == 30
        assert p.bpm is None
        assert p.guidance_scale == 7.0

    def test_custom(self):
        p = PresetInfo(
            id="x",
            name="X",
            description="desc",
            tags=["a", "b"],
            duration=60,
            bpm=120,
            key="Am",
            guidance_scale=9.0,
        )
        assert p.bpm == 120
        assert p.key == "Am"
        assert len(p.tags) == 2

    def test_frozen(self):
        p = PresetInfo(id="test", name="Test", description="test desc")
        try:
            p.duration = 99  # type: ignore[misc]
            assert False, "Should have raised"
        except AttributeError:
            pass
