"""Shared types for the ACE-Step client library."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


@dataclass(frozen=True, slots=True)
class PresetInfo:
    """A named preset for quick music generation."""

    id: str
    name: str
    description: str
    tags: list[str] = field(default_factory=list)
    duration: int = 30
    bpm: int | None = None
    key: str | None = None
    guidance_scale: float = 7.0
