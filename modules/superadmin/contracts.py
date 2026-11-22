"""External contracts for Super Admin (ADR-0013)."""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from modules.superadmin.models import RoleAssignmentRecord, UserAccountRecord


def get_user_account_records(user_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    # Plural contract getter for user account administrative status.
    records = UserAccountRecord.objects.filter(user_id__in=user_ids)
    return {
        r.user_id: {
            "institute_id": r.institute_id,
            "email": r.email,
            "user_type": r.user_type,
            "activation_status": r.activation_status,
            "deactivation_date": r.deactivation_date,
            "archival_date": r.archival_date,
            "reversibility_expires_at": r.reversibility_expires_at,
        }
        for r in records
    }


def get_active_role_assignments(user_ids: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    # Plural contract getter for active held additional roles.
    assignments = RoleAssignmentRecord.objects.filter(
        user_id__in=user_ids,
        status__in=["ACTIVE", "EXTENDED"],
    )
    result: dict[int, list[dict[str, Any]]] = {uid: [] for uid in user_ids}
    for a in assignments:
        result.setdefault(a.user_id, []).append(
            {
                "assignment_id": a.pk,
                "role_name": a.role_name,
                "scope_type": a.scope_type,
                "scope_id": a.scope_id,
                "valid_from": a.valid_from,
                "valid_to": a.valid_to,
            }
        )
    return result


def get_archived_user_statuses(user_ids: Sequence[int]) -> dict[int, dict[str, Any]]:
    # Plural contract getter for archival and reversibility window expiration.
    records = UserAccountRecord.objects.filter(user_id__in=user_ids)
    return {
        r.user_id: {
            "activation_status": r.activation_status,
            "is_archived": r.activation_status in ["ARCHIVED_REVERSIBLE", "ARCHIVED_PERMANENT"],
            "is_permanently_non_restorable": r.activation_status == "ARCHIVED_PERMANENT",
            "reversibility_expires_at": r.reversibility_expires_at,
        }
        for r in records
    }
