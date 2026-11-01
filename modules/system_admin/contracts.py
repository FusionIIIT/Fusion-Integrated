"""System Admin module's public surface.

THE ONLY THING OTHER MODULES MAY IMPORT FROM modules.system_admin.
Plural by signature per Fusion architecture rule (contracts_are_plural).
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from django.utils import timezone

from modules.system_admin.models import BasicUser, RoleAssignment


@dataclass(frozen=True)
class RoleDTO:
    assignment_id: int
    user_id: int
    role_code: str
    role_name: str
    module_association: str
    scope_type: str
    scope_id: str
    start_date: date
    end_date: date | None
    status: str


@dataclass(frozen=True)
class BasicUserDTO:
    user_id: int
    institute_id: str
    user_type: str
    email: str
    display_name: str
    department: str
    status: str
    is_active: bool


def get_user_roles(user_ids: Sequence[int]) -> dict[int, list[RoleDTO]]:
    """Batched query returning all active role assignments per user."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = (
        RoleAssignment.objects.filter(user_id__in=ids, status="active")
        .select_related("role")
        .order_by("user_id", "role__name")
    )

    result: dict[int, list[RoleDTO]] = {uid: [] for uid in ids}
    for r in rows:
        result[r.user_id].append(
            RoleDTO(
                assignment_id=r.id,
                user_id=r.user_id,
                role_code=r.role.code,
                role_name=r.role.name,
                module_association=r.role.module_association,
                scope_type=r.scope_type,
                scope_id=r.scope_id,
                start_date=r.start_date,
                end_date=r.end_date,
                status=r.status,
            )
        )
    return result


def get_active_role_codes(user_ids: Sequence[int]) -> dict[int, list[str]]:
    """Returns active role codes per user id."""
    roles_map = get_user_roles(user_ids)
    return {uid: [r.role_code for r in roles] for uid, roles in roles_map.items()}


def get_basic_users_info(user_ids: Sequence[int]) -> dict[int, BasicUserDTO]:
    """Batched query returning baseline identity data per user."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    users = BasicUser.objects.filter(user_id__in=ids)
    return {
        u.user_id: BasicUserDTO(
            user_id=u.user_id,
            institute_id=u.institute_id,
            user_type=u.user_type,
            email=u.email,
            display_name=f"{u.first_name} {u.last_name}",
            department=u.department,
            status=u.status,
            is_active=(u.status == "active"),
        )
        for u in users
    }


def get_previous_holder_audit_access(user_ids: Sequence[int]) -> dict[int, list[dict]]:
    """BR-SA-013: Returns active read-only audit permissions for past role holders."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    now = timezone.now()
    rows = RoleAssignment.objects.filter(
        user_id__in=ids,
        status="reassigned",
        previous_holder_audit_until__isnull=False,
        previous_holder_audit_until__gt=now,
    ).select_related("role")

    result: dict[int, list[dict]] = {uid: [] for uid in ids}
    for r in rows:
        result[r.user_id].append({
            "role_code": r.role.code,
            "role_name": r.role.name,
            "audit_until": r.previous_holder_audit_until.isoformat(),
            "scope_type": r.scope_type,
            "scope_id": r.scope_id,
        })
    return result
