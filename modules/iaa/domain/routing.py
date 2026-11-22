"""Where an approval goes next: the next level, else the escalation authority (BR-001, BR-401)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Target:
    level: int
    designation: str


def next_authority(levels: tuple[str, ...] | list[str], level: int,
                   escalation_designation: str) -> Target | None:
    if level + 1 < len(levels):
        return Target(level + 1, levels[level + 1])
    if escalation_designation and level < len(levels):
        return Target(len(levels), escalation_designation)
    return None


def is_final_level(levels: tuple[str, ...] | list[str], level: int) -> bool:
    return level + 1 >= len(levels)
