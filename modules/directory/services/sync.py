"""Keeps the local projection fresh from IAM."""
from __future__ import annotations

import logging
from collections.abc import Iterable

from fusion_auth.client import IamUnavailable, get_client
from modules.directory.models import UserRef

log = logging.getLogger("fusion.directory")


def ensure_users_cached(user_ids: Iterable[int]) -> int:
    """Pull anyone we have not seen yet. Never raises: a directory miss must
    degrade a screen, not break the request that needed a name."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return 0
    known = set(UserRef.objects.filter(user_id__in=ids).values_list("user_id", flat=True))
    missing = ids - known
    if not missing:
        return 0
    try:
        fetched = get_client().get_users(sorted(missing))
    except IamUnavailable as exc:
        log.warning("directory.sync_failed missing=%d err=%s", len(missing), exc)
        return 0
    return upsert(fetched.values())


def upsert(refs) -> int:
    rows = [
        UserRef(
            user_id=r.user_id, username=r.username, display_name=r.display_name,
            kind=r.kind or "student", email=r.email, department=r.department,
            programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
        )
        for r in refs
    ]
    if not rows:
        return 0
    UserRef.objects.bulk_create(
        rows, update_conflicts=True, unique_fields=["user_id"],
        update_fields=["username", "display_name", "kind", "email", "department",
                       "programme", "discipline", "batch_year", "updated_at"],
    )
    return len(rows)
