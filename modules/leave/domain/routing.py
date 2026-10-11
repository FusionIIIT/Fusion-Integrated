"""Resolving the processing/sanctioning path (BR-EL-019, BR-EL-016, BR-EL-020).

BR-EL-019: the path is resolved from the applicant, the organizational unit,
the designation/role, the leave category and the *current* hierarchy
configuration; the Establishment step and the offices Deputy Registrar (Estt.),
Dean, Registrar and Director occur only where configured.

Pure Python: the configuration arrives as plain mappings (the selector reads
`HierarchyStep` and hands them over), which is what keeps this testable without
a database and keeps a query out of a policy decision.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass

from modules.leave.domain import categories as cat

UNIT_HEAD = "unit_head"
ESTABLISHMENT = "establishment"
SANCTION = "sanction"

#: Used when nothing is configured for a higher-sanction category. The Registrar
#: is the institute's residual competent authority; without a default a
#: higher-sanction request would be unroutable the day a step is deleted.
DEFAULT_AUTHORITY = "registrar"

#: Offices that may act as the final sanctioning authority, most senior last.
AUTHORITIES = ("deputy_registrar_estt", "dean", "registrar", "director")

#: The designation each configured office is held under, as the IAM reports it.
#: This is the structural adapter between ELM's routing vocabulary and Fusion's
#: designation strings: the route says *which office* owns the step, and the
#: task finds its holder by that designation.
OFFICE_ROLES: dict[str, str] = {
    "deputy_registrar_estt": "Deputy Registrar",
    "dean": "Dean Academic",
    "registrar": "Registrar",
    "director": "Director",
    ESTABLISHMENT: "Deputy Registrar",
}

#: The applicant's unit, as the IAM reports it, to the designation that heads it.
#: A unit that is not listed resolves to `HOD (<unit>)`, which no designation
#: matches — and then the configured SLA escalation reassigns it rather than
#: leaving it invisible.
UNIT_HEADS: dict[str, str] = {
    "CSE": "HOD (CSE)",
    "ECE": "HOD (ECE)",
    "ME": "HOD (ME)",
    "ME/FT": "HOD (ME)",
    "Design": "HOD (Design)",
    "Natural Sciences": "HOD (NS)",
    "NS": "HOD (NS)",
    "Liberal Arts": "HOD (Liberal Arts)",
}


def unit_head_role(unit: str) -> str:
    """The designation that reviews requests from this unit (ACT-03)."""
    unit = (unit or "").strip()
    if unit in UNIT_HEADS:
        return UNIT_HEADS[unit]
    upper = unit.upper()
    for key, role in UNIT_HEADS.items():
        if key.upper() == upper:
            return role
    return f"HOD ({unit})" if unit else "HOD"


def role_for_step(step: Step, *, unit: str = "") -> str:
    if step.kind == UNIT_HEAD:
        return unit_head_role(unit)
    return OFFICE_ROLES.get(step.authority or step.kind, "Registrar")


@dataclass(frozen=True)
class Step:
    order: int
    kind: str
    authority: str = ""
    label: str = ""

    @property
    def task_class(self) -> str:
        """Stable key the SLA thresholds are configured against."""
        if self.kind == SANCTION:
            return f"sanction.{self.authority or DEFAULT_AUTHORITY}"
        return self.kind


def _selectivity(rule: Mapping) -> int:
    """How specific a configured rule is: 1 per non-empty selector it fixes."""
    return sum(1 for key in ("category", "unit", "designation")
               if (rule.get(key) or "").strip())


def _matches(rule: Mapping, *, category: str, unit: str, designation: str) -> bool:
    for key, value in (("category", category), ("unit", unit),
                       ("designation", designation)):
        fixed = (rule.get(key) or "").strip()
        if fixed and fixed != value:
            return False
    return True


def select_rules(rules: Iterable[Mapping], *, category: str, unit: str = "",
                 designation: str = "") -> list[Mapping]:
    """The most specific configured rule set for this request context."""
    usable = [r for r in rules if r.get("is_active", True)
              and _matches(r, category=category, unit=unit, designation=designation)]
    if not usable:
        return []
    best = max(_selectivity(r) for r in usable)
    return [r for r in usable if _selectivity(r) == best]


def resolve_route(*, category: str, unit: str = "", designation: str = "",
                  rules: Sequence[Mapping] = (),
                  applicant_is_director: bool = False) -> tuple[Step, ...]:
    """The ordered steps this request must pass through.

    A Director-applicant follows the Director-specific self-sanction path
    (BR-EL-020), which replaces the normal Unit Head / higher-authority route
    entirely — so the route is the Director step alone.
    """
    if applicant_is_director:
        return (Step(order=1, kind=SANCTION, authority="director",
                     label="Director self-sanction"),)

    wanted = "any" if cat.UNIT_HEAD_FINAL.issuperset({category}) else "higher"
    configured = sorted(
        (r for r in select_rules(rules, category=category, unit=unit,
                                 designation=designation)
         if r.get("step_kind") in (UNIT_HEAD, ESTABLISHMENT, SANCTION)),
        key=lambda r: int(r.get("step_order", 0)))

    steps = [Step(order=int(r.get("step_order", 0)), kind=r["step_kind"],
                  authority=(r.get("authority") or ""),
                  label=(r.get("label") or ""))
             for r in configured]

    if not any(s.kind == UNIT_HEAD for s in steps):
        # Every path begins at the applicant's own Unit Head: final for CL/RH,
        # reviewer for anything that needs higher sanction.
        steps.insert(0, Step(order=0, kind=UNIT_HEAD, label="Unit Head review"))

    if category in cat.HIGHER_SANCTION and not any(s.kind == SANCTION for s in steps):
        steps.append(Step(order=99, kind=SANCTION, authority=DEFAULT_AUTHORITY,
                          label="Final sanctioning decision"))

    steps.sort(key=lambda s: s.order)
    if wanted == "any":
        # A CL/RH request is decided at the Unit Head: whatever was configured
        # above that is not part of this category's path (BR-EL-016).
        return tuple(s for s in steps if s.kind != SANCTION)
    return tuple(steps)


def establishment_configured(route: Sequence[Step]) -> bool:
    """Whether an Establishment step exists for this path (BR-EL-019)."""
    return any(s.kind == ESTABLISHMENT for s in route)


def sanction_step(route: Sequence[Step]) -> Step | None:
    for s in reversed(tuple(route)):
        if s.kind == SANCTION:
            return s
    return None


def step_at(route: Sequence[Step], index: int) -> Step | None:
    return route[index] if 0 <= index < len(route) else None
