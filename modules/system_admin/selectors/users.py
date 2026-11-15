"""User and profile selectors for system_admin."""
from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta
from typing import Optional, Tuple

from django.db.models import Q
from django.utils import timezone

from modules.system_admin.constants import UserLifecycleStatus
from modules.system_admin.models import BasicUser, UserProfile, UserStatusHistory


def get_user_by_id(user_id: int) -> Optional[BasicUser]:
    """Retrieve basic user with profile loaded via select_related."""
    return BasicUser.objects.filter(id=user_id).select_related("profile").first()


def get_user_by_institute_id(institute_id: str) -> Optional[BasicUser]:
    """Case-insensitive lookup by institutional identifier."""
    if not institute_id:
        return None
    return (
        BasicUser.objects.filter(institute_id__iexact=institute_id.strip())
        .select_related("profile")
        .first()
    )


def get_user_by_username(username: str) -> Optional[BasicUser]:
    """Lookup by username."""
    if not username:
        return None
    return BasicUser.objects.filter(username=username.strip()).select_related("profile").first()


def list_users(
    *,
    kind: Optional[str] = None,
    status: Optional[str] = None,
    q: str = "",
    limit: int = 50,
    offset: int = 0,
) -> Tuple[Sequence[BasicUser], int]:
    """Filter and paginate users."""
    qs = BasicUser.objects.select_related("profile").order_by("-created_at")
    if kind:
        qs = qs.filter(kind=kind)
    if status:
        qs = qs.filter(status=status)
    if q:
        query = q.strip()
        qs = qs.filter(
            Q(username__icontains=query)
            | Q(institute_id__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__display_name__icontains=query)
        )
    total = qs.count()
    return list(qs[offset : offset + limit]), total


def get_deactivated_users_eligible_for_archival(
    min_deactivation_days: int = 30,
) -> Sequence[BasicUser]:
    """Find deactivated users whose deactivation period exceeds minimum threshold (BR-SA-004)."""
    cutoff = timezone.now() - timedelta(days=min_deactivation_days)
    return list(
        BasicUser.objects.filter(
            status=UserLifecycleStatus.DEACTIVATED, deactivated_at__lte=cutoff
        ).select_related("profile")
    )


def get_user_status_history(user_id: int) -> Sequence[UserStatusHistory]:
    """Ordered status transition history for an account."""
    return list(
        UserStatusHistory.objects.filter(user_id=user_id).order_by("-effective_timestamp")
    )


def get_user_profile(user_id: int) -> Optional[UserProfile]:
    """Retrieve profile object for a user."""
    return UserProfile.objects.filter(user_id=user_id).first()
