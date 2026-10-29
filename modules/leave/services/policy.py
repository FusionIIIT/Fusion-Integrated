"""Read the current policy, and resolve which authority handles a request.

There is exactly one policy row (BR-EL-030) and it is read, not selected by a
version, because the specification forbids a leave-policy version lifecycle.
"""
from __future__ import annotations

from modules.leave.domain import routing as routing_domain
from modules.leave.models import HierarchyRoute, LeavePolicy, OrganizationalUnit

#: Which kinds of person may take which leave (BR-EL-003, BR-EL-008).
DEFAULT_CATEGORY_KINDS: dict[str, frozenset[str]] = {
    "CASUAL": frozenset({"faculty", "staff"}),
    "RH": frozenset({"faculty", "staff"}),
    "SCL": frozenset({"faculty", "staff"}),
    "EL": frozenset({"staff"}),
    "COL": frozenset({"faculty", "staff"}),
    "VL": frozenset({"faculty"}),
}

DEFAULT_SUBSTITUTE_REQUIRED_FOR: tuple[str, ...] = ("SCL", "EL", "COL", "VL")


def current_policy() -> LeavePolicy:
    """Get-or-create the single row, so a fresh database is still usable."""
    row = LeavePolicy.objects.first()
    if row is not None:
        return row
    return LeavePolicy.objects.create(
        substitute_required_for=list(DEFAULT_SUBSTITUTE_REQUIRED_FOR),
        category_kinds={key: sorted(value)
                        for key, value in DEFAULT_CATEGORY_KINDS.items()})


def org_unit_for(department: str) -> OrganizationalUnit | None:
    if not department:
        return None
    return OrganizationalUnit.objects.filter(
        name__iexact=department.strip(), is_active=True).first()


def unit_head_for(department: str) -> int | None:
    unit = org_unit_for(department)
    return None if unit is None else unit.head_user_id


def applicant_is_director(actor, policy: LeavePolicy | None = None) -> bool:
    """BR-EL-022: a Director is also the final authority for their own leave, and
    the Director may be a configured role rather than a person in the directory."""
    role = getattr(actor, "active_role", None) or ""
    return "director" in role.lower()


def is_director_user(user_id: int | None) -> bool:
    """EL-UC-015: the system may know the Director from configuration."""
    from modules.leave.models import HierarchyRouteStep

    if user_id is None:
        return False
    return HierarchyRouteStep.objects.filter(
        user_id=user_id, kind=routing_domain.DIRECTOR_SELF_SANCTION_STEP).exists()


def route_for(category: str, *, org_unit: OrganizationalUnit | None = None
              ) -> HierarchyRoute | None:
    """The most specific active route: unit+category, then category, then unit."""
    qs = HierarchyRoute.objects.filter(is_active=True).prefetch_related("steps")
    for lookup in ({"org_unit": org_unit, "leave_category": category},
                   {"leave_category": category, "org_unit__isnull": True},
                   {"leave_category": "", "org_unit": org_unit},
                   {"leave_category": "", "org_unit__isnull": True}):
        if all(v is None for v in lookup.values()):
            continue
        match = qs.filter(**lookup).order_by("id").first()
        if match is not None:
            return match
    return None


def resolved_route(category: str, *,
                   org_unit: OrganizationalUnit | None = None
                   ) -> routing_domain.Route:
    row = route_for(category, org_unit=org_unit)
    return routing_domain.Route() if row is None else row.as_domain()


def substitute_required(category: str, policy: LeavePolicy | None = None) -> bool:
    """BR-EL-014. A policy with no configured list falls back to the categories
    the specification requires, rather than to nobody."""
    pol = policy or current_policy()
    configured = tuple(pol.substitute_required_for or ())
    target = configured or DEFAULT_SUBSTITUTE_REQUIRED_FOR
    return category in target


def entitlement_days(kind: str, category: str, policy: LeavePolicy) -> float | None:
    """The configured entitlement for this person's kind, or None when the
    policy grants none, so the caller can say so plainly rather than guess."""
    table: dict[str, dict[str, object]] = {
        "faculty": {"CL": policy.casual_days, "RH": policy.restricted_holiday_days,
                    "SCL": policy.special_casual_days, "COL": policy.commuted_days,
                    "VL": policy.vacation_days},
        "staff": {"CL": policy.casual_days, "RH": policy.restricted_holiday_days,
                  "SCL": policy.special_casual_days, "COL": policy.commuted_days,
                  "EL": policy.earned_days},
    }
    value = table.get(kind, {}).get(category)
    return None if value is None else float(value)


def category_allowed(kind: str, category: str, policy: LeavePolicy) -> bool:
    kinds = policy.category_kinds or DEFAULT_CATEGORY_KINDS
    allowed = frozenset(kinds.get(category) or ())
    return not allowed or kind in allowed