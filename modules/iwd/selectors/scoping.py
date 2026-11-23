"""Queryset scoping by role and principal (Step 2.5). Scope failure yields 404, never 403."""

from __future__ import annotations

from typing import Any

from django.db.models import QuerySet

from modules.iwd.models import Complaint


def scope_complaints(
    principal: Any, base_qs: QuerySet[Complaint] | None = None
) -> QuerySet[Complaint]:
    """Narrow complaints queryset based on the active role and user ID of the principal."""
    qs = base_qs if base_qs is not None else Complaint.objects.all()

    if principal is None:
        return qs.none()

    user_id = getattr(principal, "user_id", None)
    active_role = getattr(principal, "active_role", None)

    # Privileged staff with overarching oversight
    if active_role in [
        "iwd_admin",
        "iwd_department_head",
        "iwd_director",
        "iwd_auditor",
        "iwd_accounts",
    ]:
        return qs

    # Engineer sees complaints assigned to them
    if active_role == "iwd_engineer":
        return qs.filter(assigned_engineer_id=user_id)

    # Plain employee/student/faculty sees only their own submitted complaints
    if user_id is not None:
        return qs.filter(requester_user_id=user_id)

    return qs.none()
