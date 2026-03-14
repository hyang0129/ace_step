"""Tests for ace_step.mood -- mood-to-preset matching."""

from __future__ import annotations

from ace_step.mood import match_preset


class TestMatchPreset:
    def test_epic_maps_to_history(self):
        p = match_preset("epic dramatic cinematic")
        assert p.id == "history_epic"

    def test_suspenseful_maps_to_investigation(self):
        p = match_preset("tense suspenseful mystery")
        assert p.id == "investigation_tension"

    def test_cheerful_maps_to_travel(self):
        p = match_preset("cheerful adventure travel")
        assert p.id == "travel_upbeat"

    def test_peaceful_nature(self):
        p = match_preset("peaceful serene nature")
        assert p.id == "nature_peaceful"

    def test_science_curious(self):
        p = match_preset("curious educational science")
        assert p.id == "science_curiosity"

    def test_warm_intimate(self):
        p = match_preset("warm nostalgic intimate")
        assert p.id == "biography_warm"

    def test_corporate_neutral(self):
        p = match_preset("corporate business economics")
        assert p.id == "economics_neutral"

    def test_ambient_documentary(self):
        p = match_preset("ambient atmospheric reflective")
        assert p.id == "documentary_ambient"

    def test_empty_string_returns_default(self):
        p = match_preset("")
        assert p.id == "documentary_ambient"

    def test_no_match_returns_default(self):
        p = match_preset("xyzzy gibberish foobar")
        assert p.id == "documentary_ambient"

    def test_case_insensitive(self):
        p = match_preset("EPIC DRAMATIC CINEMATIC")
        assert p.id == "history_epic"

    def test_keyword_must_appear_in_tone(self):
        """Matching checks if keyword is a substring of tone, not vice versa."""
        p = match_preset("suspenseful dark mystery")
        assert p.id == "investigation_tension"
        # 'suspense' alone does NOT match keyword 'suspenseful'
        p2 = match_preset("suspense")
        assert p2.id == "documentary_ambient"  # no keyword hit, falls back

    def test_returns_preset_info(self):
        p = match_preset("epic")
        assert p.name is not None
        assert p.description is not None
        assert p.bpm is not None
