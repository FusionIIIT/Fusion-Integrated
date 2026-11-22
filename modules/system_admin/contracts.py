"""Public contracts for cross-module integration (ADR-0008).

All getters are plural and return plain Python dictionaries to prevent N+1 queries
and avoid leaky abstractions across module boundaries.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modules.system_admin.models.role_assignment import RoleAssignment
from modules.system_admin.models.user_account import UserAccount


def get_user_admin_statuses(user_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    """Return administrative status and user type for a sequence of user IDs."""
    users = UserAccount.objects.filter(user_id__in=user_ids)
    result: dict[int, dict[str, Any]] = {}
    for u in users:
        result[u.user_id] = {
            "user_id": u.user_id,
            "institute_id": u.institute_id,
            "username": u.username,
            "user_type": u.user_type,
            "status": u.status,
            "deactivated_at": u.deactivated_at.isoformat() if u.deactivated_at else None,
        }
    return result


def get_active_role_holders(role_codes: Sequence[str]) -> dict[str, list[int]]:
    """Return active user_ids holding each specified role code."""
    assignments = RoleAssignment.objects.filter(
        role_code__in=role_codes,
        status="active",
    ).values("role_code", "user_id")

    result: dict[str, list[int]] = {code: [] for code in role_codes}
    for a in assignments:
        result[a["role_code"]].append(a["user_id"])
    return result


def get_user_effective_roles(user_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    """Return active role codes and scopes for a sequence of user IDs."""
    assignments = RoleAssignment.objects.filter(
        user_id__in=user_ids,
        status="active",
    )
    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for a in assignments:
        result[a.user_id].append({
            "role_code": a.role_code,
            "role_name": a.role_name,
            "scope": a.scope,
            "start_date": str(a.start_date),
            "end_date": str(a.end_date) if a.end_date else None,
        })
    return result
