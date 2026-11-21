"""Role definitions, assignments, and availability selectors for system_admin."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any, Dict, Optional

from modules.system_admin.constants import RoleAssignmentState
from modules.system_admin.models import RoleAssignment, RoleDefinition, RoleHandoverLog


def list_role_definitions(
    *, category: Optional[str] = None, active_only: bool = True
) -> Sequence[RoleDefinition]:
    """Retrieve role catalog definitions."""
    qs = RoleDefinition.objects.all().order_by("category", "code")
    if active_only:
        qs = qs.filter(is_active=True)
    if category:
        qs = qs.filter(category=category)
    return list(qs)


def get_role_definition(role_code: str) -> Optional[RoleDefinition]:
    """Get single role definition by code."""
    return RoleDefinition.objects.filter(code=role_code).first()


def get_role_availability(role_code: str, scope: str = "institute") -> Dict[str, Any]:
    """Check availability of role in a given scope (singular roles constraint check)."""
    role = get_role_definition(role_code)
    if not role:
        return {"error": "Role not found", "is_available": False}

    if not role.is_singular:
        return {
            "role_code": role.code,
            "label": role.label,
            "is_singular": False,
            "scope": scope,
            "is_available": True,
            "current_holder_id": None,
            "current_holder_username": None,
        }

    current = (
        RoleAssignment.objects.filter(
            role=role,
            scope=scope,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        )
        .select_related("user")
        .first()
    )

    return {
        "role_code": role.code,
        "label": role.label,
        "is_singular": True,
        "scope": scope,
        "is_available": current is None,
        "current_holder_id": current.user_id if current else None,
        "current_holder_username": current.user.username if current else None,
    }


def get_user_assignments(user_id: int) -> Sequence[RoleAssignment]:
    """All historical and active assignments for a user."""
    return list(
        RoleAssignment.objects.filter(user_id=user_id)
        .select_related("role")
        .order_by("-start_date")
    )


def get_user_active_assignments(user_id: int) -> Sequence[RoleAssignment]:
    """Active and extended assignments currently granting permissions (AFR-SA-030)."""
    return list(
        RoleAssignment.objects.filter(
            user_id=user_id,
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
        )
        .select_related("role")
        .order_by("role__category", "role__code")
    )


def get_assignments_pending_activation(today: date) -> Sequence[RoleAssignment]:
    """Scheduled assignments reaching their start date (BW-SA-04, UC-SA-028)."""
    return list(
        RoleAssignment.objects.filter(
            state=RoleAssignmentState.SCHEDULED,
            start_date__lte=today,
        ).select_related("role", "user")
    )


def get_assignments_pending_expiry(today: date) -> Sequence[RoleAssignment]:
    """Active/extended time-bound roles reaching their end date (BW-SA-03..05, UC-SA-029)."""
    return list(
        RoleAssignment.objects.filter(
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
            end_date__isnull=False,
            end_date__lte=today,
        ).select_related("role", "user")
    )


def get_assignments_approaching_expiry(lead_days: int, today: date) -> Sequence[RoleAssignment]:
    """Time-bound roles within lead time window for expiry notifications (BR-SA-016, UC-SA-030)."""
    target_date = today + timedelta(days=lead_days)
    return list(
        RoleAssignment.objects.filter(
            state__in=[RoleAssignmentState.ACTIVE, RoleAssignmentState.EXTENDED],
            end_date__isnull=False,
            end_date__gte=today,
            end_date__lte=target_date,
        ).select_related("role", "user")
    )


def get_previous_holder_audit_access(user_id: int, today: date) -> Sequence[RoleHandoverLog]:
    """Audit access logs for past role holders whose audit access is still active (BR-SA-013)."""
    return list(
        RoleHandoverLog.objects.filter(
            previous_holder_id=user_id,
            audit_access_expires_at__gte=today,
        ).select_related("role")
    )
