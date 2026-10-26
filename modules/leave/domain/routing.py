"""Who reviews and who sanctions, from the current hierarchy (BR-EL-016 to 020, BR-EL-030)."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from modules.leave.domain import categories as cat

#: Spelled as globals_designation holds it; BR-EL-020 turns on it.
DIRECTOR_DESIGNATION = "Director"


class RoutingUnresolved(Exception):
    """The configuration cannot name an authority for this request; nothing may move."""


@dataclass(frozen=True)
class OrgUnit:
    department: str
    unit_head_designation: str
    #: Reviews the Unit Head's own leave, so nobody reviews themselves.
    head_leave_designation: str = ""


@dataclass(frozen=True)
class SanctionRoute:
    sanction_designation: str
    establishment_designation: str = ""
    employee_kind: str = ""
    category: str = ""
    department: str = ""
    applicant_designation: str = ""

    @property
    def key(self) -> tuple[str, str, str, str]:
        return (self.employee_kind, self.category, self.department, self.applicant_designation)

    def matches(self, *, kind: str, category: str, department: str,
                roles: frozenset[str]) -> bool:
        return ((not self.employee_kind or self.employee_kind == kind)
                and (not self.category or self.category == category)
                and (not self.department or self.department == department)
                and (not self.applicant_designation or self.applicant_designation in roles))

    @property
    def specificity(self) -> int:
        return ((8 if self.applicant_designation else 0) + (4 if self.department else 0)
                + (2 if self.category else 0) + (1 if self.employee_kind else 0))


@dataclass(frozen=True)
class Hierarchy:
    units: dict[str, OrgUnit]
    routes: tuple[SanctionRoute, ...]
    revision_id: int | None = None


def is_director(roles: Iterable[str]) -> bool:
    return DIRECTOR_DESIGNATION in set(roles)


def unit_head(h: Hierarchy, *, department: str, roles: Iterable[str]) -> str:
    """The designation that reviews this applicant at the Unit Head step."""
    held = frozenset(roles)
    unit = h.units.get(department or "")
    if unit is None:
        raise RoutingUnresolved(
            f"No Unit Head is configured for {department or 'your unit (none is on record)'}. "
            f"Ask the Leave Administrator to set one before applying.")
    if unit.unit_head_designation not in held:
        return unit.unit_head_designation
    if unit.head_leave_designation and unit.head_leave_designation not in held:
        return unit.head_leave_designation
    raise RoutingUnresolved(
        f"You are the Unit Head of {department}, and no one is configured to review the Unit "
        f"Head's own leave. Ask the Leave Administrator to set it.")


def sanction_route(h: Hierarchy, *, kind: str, category: str, department: str,
                   roles: Iterable[str]) -> SanctionRoute:
    """BR-EL-018/019: the most specific configured route; never one that reaches the applicant."""
    held = frozenset(roles)
    found = sorted((r for r in h.routes
                    if r.matches(kind=kind, category=category, department=department,
                                 roles=held)),
                   key=lambda r: -r.specificity)
    if not found:
        raise RoutingUnresolved(
            f"No sanctioning authority is configured for {cat.LABELS.get(category, category)} "
            f"for {kind or 'this employee'}. Ask the Leave Administrator to configure one.")
    route = found[0]
    if route.sanction_designation in held or route.establishment_designation in held:
        raise RoutingUnresolved(
            "This leave would be routed to you for your own decision. Ask the Leave "
            "Administrator to configure a route for your designation.")
    return route


def validate(h: Hierarchy, *, reviewers: frozenset[str], establishments: frozenset[str],
             authorities: frozenset[str]) -> list[str]:
    """Every named designation must hold the permission its step needs (registry.ROLE_GRANTS)."""
    problems: list[str] = []
    for unit in h.units.values():
        if not unit.department.strip():
            problems.append("A unit needs a department name.")
        if unit.unit_head_designation not in reviewers:
            problems.append(f"{unit.department}: {unit.unit_head_designation!r} cannot review "
                            f"leave. Choose one of: {', '.join(sorted(reviewers))}.")
        if unit.head_leave_designation and unit.head_leave_designation not in reviewers:
            problems.append(f"{unit.department}: {unit.head_leave_designation!r} cannot review "
                            f"the Unit Head's leave.")
        if unit.head_leave_designation and (
                unit.head_leave_designation == unit.unit_head_designation):
            problems.append(f"{unit.department}: the Unit Head cannot review their own leave.")
    seen: set[tuple[str, str, str, str]] = set()
    for r in h.routes:
        if r.key in seen:
            problems.append(f"Two routes match exactly the same requests: {r.key}.")
        seen.add(r.key)
        if r.sanction_designation not in authorities:
            problems.append(f"{r.sanction_designation!r} cannot sanction leave. Choose one of: "
                            f"{', '.join(sorted(authorities))}.")
        if r.establishment_designation and r.establishment_designation not in establishments:
            problems.append(f"{r.establishment_designation!r} cannot perform the Establishment "
                            f"step. Choose one of: {', '.join(sorted(establishments))}.")
        if r.employee_kind and r.employee_kind not in cat.EMPLOYEE_KINDS:
            problems.append(f"{r.employee_kind!r} is not an employee kind.")
        if r.category and (r.category not in cat.CATEGORIES or cat.get(r.category).unit_head_final):
            problems.append(f"{r.category!r} is not a higher-sanction category.")
    return problems
