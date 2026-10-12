from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Dict, List

from django.db.models import QuerySet

from .models import (
    LeaveApplication,
    LeaveBalance,
    HolidayCalendar,
    Holiday,
    VacationPeriod,
    OrganizationalUnit,
    LeaveHierarchy,
    LeaveHierarchyStep,
    LeavePolicy,
)


def get_leave_applications(user_ids: Sequence[int]) -> List[Dict[str, Any]]:
    """Retrieve leave applications for given user IDs.

    Returns a list of dictionaries containing application details grouped by user.
    """
    qs = LeaveApplication.objects.filter(user_id__in=user_ids).select_related(
        "unit_head_user_id",
        "substitute_user_id",
        "final_decision_user_id",
    ).prefetch_related("transactions", "tasks")

    result: Dict[int, List[Dict[str, Any]]] = {}
    for app in qs:
        user_id = app.user_id
        if user_id not in result:
            result[user_id] = []
        result[user_id].append({
            "id": app.id,
            "category": app.category,
            "start_date": app.start_date.isoformat(),
            "end_date": app.end_date.isoformat(),
            "purpose": app.purpose,
            "status": app.status,
            "unit_head_user_id": app.unit_head_user_id,
            "substitute_user_id": app.substitute_user_id,
            "final_decision_user_id": app.final_decision_user_id,
        })

    return list(result.values())


def get_leave_balances(user_ids: Sequence[int]) -> List[Dict[str, Any]]:
    """Retrieve leave balances for given user IDs.

    Returns a list of dictionaries containing balance snapshots grouped by user.
    """
    qs = LeaveBalance.objects.filter(user_id__in=user_ids).select_related()

    result: Dict[int, List[Dict[str, Any]]] = {}
    for bal in qs:
        user_id = bal.user_id
        if user_id not in result:
            result[user_id] = []
        result[user_id].append({
            "effective_date": bal.effective_date.isoformat(),
            "cl_balance": float(bal.cl_balance),
            "rh_balance": float(bal.rh_balance),
            "scl_balance": float(bal.scl_balance),
            "el_balance": float(bal.el_balance),
            "col_balance": float(bal.col_balance),
            "vl_balance": float(bal.vl_balance),
        })

    return list(result.values())


def _get_holidays(year: int) -> List[Dict[str, Any]]:
    """Retrieve holidays for a given year."""
    calendar = HolidayCalendar.objects.filter(year=year, is_effective=True).first()
    if not calendar:
        return []
    return [
        {
            "date": h.date.isoformat(),
            "type": h.type,
            "name": h.name,
        }
        for h in Holiday.objects.filter(calendar=calendar)
    ]


def _get_vacation_periods(year: int) -> List[Dict[str, Any]]:
    """Retrieve vacation periods for a given year."""
    return [
        {
            "year": vp.year,
            "name": vp.name,
            "start_date": vp.start_date.isoformat(),
            "end_date": vp.end_date.isoformat(),
        }
        for vp in VacationPeriod.objects.filter(year=year)
    ]


def get_organizational_units() -> List[Dict[str, Any]]:
    """Retrieve all organizational units."""
    return [
        {
            "id": u.id,
            "code": u.code,
            "name": u.name,
            "parent_unit_id": u.parent_unit_id,
            "unit_head_user_id": u.unit_head_user_id,
        }
        for u in OrganizationalUnit.objects.all()
    ]


def get_leave_hierarchies() -> List[Dict[str, Any]]:
    """Retrieve all leave hierarchies and their steps."""
    hierarchies = LeaveHierarchy.objects.all()
    result: Dict[str, List[Dict[str, Any]]] = {}

    for h in hierarchies:
        if h.name not in result:
            result[h.name] = []
        result[h.name].append({
            "order": s.order,
            "role_code": s.role_code,
            "is_establishment_step": s.is_establishment_step,
        } for s in h.steps.all())

    return [{"name": k, "steps": v} for k, v in result.items()]


def get_leave_policy() -> Dict[str, Any]:
    """Retrieve current leave policy configuration."""
    policy = LeavePolicy.objects.first()
    if not policy:
        return {}
    return {
        "CL_DAYS": policy.CL_DAYS,
        "RH_DAYS": policy.RH_DAYS,
        "SCL_MAX_DAYS": policy.SCL_MAX_DAYS,
        "EL_DAYS": policy.EL_DAYS,
        "COL_DAYS": policy.COL_DAYS,
        "VL_DAYS": policy.VL_DAYS,
        "VL_TO_EL_RATIO": float(policy.VL_TO_EL_RATIO),
    }
