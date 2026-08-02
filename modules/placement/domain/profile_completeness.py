"""Profile completeness (PC-BR-001). Pure functions.

PC-BR-001 says PCMS enforces completeness "where such completeness is
required" — so the requirement is data, not code. The weights below are the
default the placement office starts from; what matters architecturally is that
the answer is a computed percentage plus a NAMED LIST of what is missing, never
a bare boolean. A student blocked from applying is told which three fields to
fill in, not that they are "incomplete".
"""
from __future__ import annotations

from dataclasses import dataclass

# (key, human label, weight). Weights are relative, not percentages.
REQUIREMENTS: tuple[tuple[str, str, int], ...] = (
    ("headline", "A one-line headline", 5),
    ("about", "A short summary", 10),
    ("phone", "Contact phone number", 10),
    ("skills", "At least three skills", 20),
    ("education", "Education history", 15),
    ("projects", "At least one project", 15),
    ("resume", "An uploaded resume", 25),
)

TOTAL_WEIGHT = sum(w for _, _, w in REQUIREMENTS)

# The bar for "complete enough to apply". Below this, applications are blocked.
REQUIRED_PERCENT = 80

MIN_SKILLS = 3


@dataclass(frozen=True)
class Completeness:
    percent: int
    is_complete: bool
    missing: list[dict]

    @property
    def missing_keys(self) -> list[str]:
        return [m["field"] for m in self.missing]


def _present(key: str, data: dict) -> bool:
    value = data.get(key)
    if key == "skills":
        return isinstance(value, (list, tuple)) and len(
            [s for s in value if str(s).strip()]) >= MIN_SKILLS
    if key in ("education", "projects"):
        return isinstance(value, (list, tuple)) and len(value) > 0
    if key == "resume":
        return bool(value)
    return bool(str(value or "").strip())


def evaluate(data: dict) -> Completeness:
    """`data` is the profile's fields plus `resume` (truthy if one exists)."""
    earned = 0
    missing: list[dict] = []
    for key, label, weight in REQUIREMENTS:
        if _present(key, data):
            earned += weight
        else:
            missing.append({"field": key, "label": label, "weight": weight})

    percent = round(earned * 100 / TOTAL_WEIGHT)
    return Completeness(percent=percent,
                        is_complete=percent >= REQUIRED_PERCENT,
                        missing=missing)
