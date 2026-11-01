"""Cross-module public contracts for Super Admin (ADR-0013)."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TypedDict

from modules.superadmin.models import RoleAssignment, UserAccount


class UserAccountDTO(TypedDict):
    user_id: int
    institute_id: str
    email: str
    status: str


def get_user_accounts(user_ids: Sequence[int]) -> list[UserAccountDTO]:
    """Plural getter: Fetch basic user profiles for given IDs."""
    if not user_ids:
        return []
    return [
        UserAccountDTO(
            user_id=u.user_id,
            institute_id=u.institute_id,
            email=u.email,
            status=u.status,
        )
        for u in UserAccount.objects.filter(user_id__in=user_ids)
    ]


def get_active_roles_for_users(user_ids: Sequence[int]) -> dict[int, list[str]]:
    """Plural getter: Fetch active roles for given user IDs."""
    if not user_ids:
        return {}
    res: dict[int, list[str]] = {uid: [] for uid in user_ids}
    roles = RoleAssignment.objects.filter(
        user_id__in=user_ids, status="ACTIVE"
    ).values_list("user_id", "role_code")
    for uid, code in roles:
        if uid in res:
            res[uid].append(code)
    return res
