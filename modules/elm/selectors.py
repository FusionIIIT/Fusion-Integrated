"""Read paths. Ownership and scope live here, not in views."""
from __future__ import annotations

import re

from django.db.models import Q

from modules.elm.models import LeaveApplication, LeaveBalance

#: Statuses that count as "active" for overlap purposes (PS §5 / BR-EL-012).
ACTIVE_STATUSES = ("submitted", "forwarded", "approved", "cancel_req", "res_req")


def _extract_hod_dept(role_name: str | None) -> str | None:
    if not role_name:
        return None
    m = re.search(r"HOD\s*\(([^)]+)\)", role_name, re.IGNORECASE)
    return m.group(1).strip() if m else None


def visible_applications(principal):
    """Applications the caller may see: their own, or scoped by their authority role."""
    if not principal.has_permission("elm.application.view"):
        return LeaveApplication.objects.filter(user_id=principal.user_id)

    # Scoped Unit Head view
    dept = _extract_hod_dept(principal.active_role)
    if dept:
        return LeaveApplication.objects.filter(
            Q(user_id=principal.user_id) | Q(department__iexact=dept)
        )

    # Institute-level authority (Deans, Registrar, Director, Leave Admin)
    return LeaveApplication.objects.all()


def inbox_applications(principal):
    """Actionable workflow requests awaiting caller's recommendation or decision."""
    dept = _extract_hod_dept(principal.active_role)
    if dept:
        # Unit Head inbox: department applications in submitted or cancel_req
        return (LeaveApplication.objects
                .filter(department__iexact=dept,
                        status__in=["submitted", "cancel_req"])
                .exclude(user_id=principal.user_id)
                .order_by("start_date"))

    # Sanctioning authorities (Dean, Registrar, Director)
    return (LeaveApplication.objects
            .filter(status__in=["forwarded", "cancel_req", "res_req"])
            .exclude(user_id=principal.user_id)
            .order_by("start_date"))


def substitute_inbox_applications(user_id: int):
    """Pending requests where caller is nominated as substitute."""
    return (LeaveApplication.objects
            .filter(substitute_user_id=user_id,
                    substitute_status="pending",
                    status__in=["submitted", "forwarded"])
            .order_by("start_date"))


def balances_for(user_id: int, year: int):
    return (LeaveBalance.objects
            .filter(user_id=user_id, year=year)
            .order_by("category"))
