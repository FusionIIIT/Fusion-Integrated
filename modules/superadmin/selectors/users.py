"""User selectors for Super Admin."""

from __future__ import annotations

from django.db.models import QuerySet

from modules.superadmin.models import UserAccountRecord
from modules.superadmin.selectors.scoping import visible_users


def list_users(
    principal,
    *,
    search: str = "",
    user_type: str = "",
    status: str = "",
) -> QuerySet[UserAccountRecord]:
    qs = visible_users(principal)
    if search:
        qs = qs.filter(institute_id__icontains=search) | qs.filter(email__icontains=search)
    if user_type:
        qs = qs.filter(user_type=user_type.upper())
    if status:
        qs = qs.filter(activation_status=status.upper())
    return qs.order_by("-created_at")


def get_user_by_id(principal, user_id: int) -> UserAccountRecord | None:
    return visible_users(principal).filter(user_id=user_id).first()


def get_user_by_institute_id(principal, institute_id: str) -> UserAccountRecord | None:
    return visible_users(principal).filter(institute_id=institute_id).first()
