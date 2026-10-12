"""Policy reads and configuration (BR-EL-001…014, BR-EL-030).

The policy row is a singleton; entitlements, the leave-year boundary and the
substitute gate all read from here so a rule never hard-codes a number.
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.leave.domain.categories import CL, COL, EL, RH, SCL, VL
from modules.leave.models import LeavePolicy
from modules.leave.services import authz

#: The only fields an admin may PUT; anything else is a 400, not silence.
EDITABLE = (
    "cl_annual", "rh_annual", "scl_annual", "el_annual_nonfaculty",
    "el_annual_faculty", "col_annual", "vl_annual_faculty",
    "vl_to_el_numerator", "vl_to_el_denominator",
    "el_carry_forward", "col_carry_forward",
    "substitute_required_categories",
    "scl_evidence_required", "col_evidence_required",
    "year_end_month", "year_end_day",
)


def current_policy() -> LeavePolicy:
    policy, _ = LeavePolicy.objects.get_or_create(id=1)
    return policy


def update_policy(actor, data: dict) -> LeavePolicy:
    authz.require(actor, "leave.type.manage")
    unknown = sorted(set(data) - set(EDITABLE))
    if unknown:
        raise BadRequestError(f"Unknown policy field {unknown[0]!r}.",
                              code="unknown_field")
    if int(data.get("vl_to_el_denominator",
                    current_policy().vl_to_el_denominator)) <= 0:
        raise BadRequestError("The VL→EL denominator cannot be zero.",
                              code="invalid_policy")
    policy = current_policy()
    for field, value in data.items():
        setattr(policy, field, value)
    policy.save()
    return policy


def is_faculty(kind: str) -> bool:
    return kind == "faculty"


def entitlement(policy: LeavePolicy, category: str, faculty: bool) -> Decimal:
    """Annual entitlement for one category (PS §2–4). VL for faculty is
    converted into EL at year end rather than granted as EL (BR-EL-005)."""
    table = {
        CL: policy.cl_annual,
        RH: policy.rh_annual,
        SCL: policy.scl_annual,
        EL: policy.el_annual_faculty if faculty else policy.el_annual_nonfaculty,
        COL: policy.col_annual,
        VL: policy.vl_annual_faculty if faculty else Decimal(0),
    }
    return table.get(category, Decimal(0))


def leave_year_of(policy: LeavePolicy, day: date) -> int:
    """Which leave year `day` belongs to. A year ends on year_end_month/
    year_end_day, so leave on the boundary still belongs to the closing year."""
    boundary = (policy.year_end_month, policy.year_end_day)
    return day.year + 1 if (day.month, day.day) > boundary else day.year


def current_leave_year(policy: LeavePolicy | None = None) -> int:
    policy = policy or current_policy()
    return leave_year_of(policy, timezone.localdate())


def substitute_required(policy: LeavePolicy, category: str) -> bool:
    """BR-EL-014: responsibility coverage for the higher categories."""
    return category in set(policy.substitute_required_categories or [])
