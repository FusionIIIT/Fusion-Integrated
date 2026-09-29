"""Keeps the local projection fresh from IAM."""
from __future__ import annotations

import logging
from collections.abc import Iterable
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef

log = logging.getLogger("fusion.directory")


def ensure_users_cached(user_ids: Iterable[int]) -> int:
    """Pull anyone we have not seen recently enough. Never raises: a directory
    miss must degrade a screen, not break the request that needed a name."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return 0
    fresh_since = timezone.now() - timedelta(seconds=settings.DIRECTORY_MAX_AGE_SECONDS)
    # Caching on first sight alone pins a person to the day they were first read.
    fresh = set(UserRef.objects.filter(user_id__in=ids, synced_at__gte=fresh_since)
                .values_list("user_id", flat=True))
    stale = ids - fresh
    if not stale:
        return 0
    try:
        fetched = get_client().get_users(sorted(stale))
    except IamUnavailable as exc:
        log.warning("directory.sync_failed stale=%d err=%s", len(stale), exc)
        return 0
    return upsert(fetched.values())


#: Column widths, read off the model so they cannot drift from the migration.
_LIMITS = {
    f.name: f.max_length
    for f in UserRef._meta.get_fields()
    if getattr(f, "max_length", None)
}


def unstorable(ref) -> str:
    """The first field this row will not fit into, or empty if it fits."""
    for field, cap in _LIMITS.items():
        value = getattr(ref, field, "") or ""
        if isinstance(value, str) and len(value) > cap:
            return f"{field} is {len(value)} characters, the column holds {cap}"
    return ""


def upsert(refs, *, rejected: list | None = None) -> int:
    rows = []
    for r in refs:
        problem = unstorable(r)
        if problem:
            log.warning("directory.row_rejected user=%s %s", r.user_id, problem)
            if rejected is not None:
                rejected.append((r.user_id, problem))
            continue
        rows.append(UserRef(
            user_id=r.user_id, username=r.username, display_name=r.display_name,
            kind=r.kind or "student", email=r.email, department=r.department,
            programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
            is_active=getattr(r, "is_active", True),
            resume_link=getattr(r, "resume_link", "") or "",
            profile_completed=getattr(r, "profile_completed", False),
        ))
    if not rows:
        return 0
    UserRef.objects.bulk_create(
        rows, update_conflicts=True, unique_fields=["user_id"],
        # Without is_active a deactivated account would stay active here.
        update_fields=["username", "display_name", "kind", "email", "department",
                       "programme", "discipline", "batch_year", "is_active",
                       "resume_link", "profile_completed", "updated_at"],
    )
    return len(rows)
