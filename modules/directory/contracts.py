"""directory's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.directory.models import UserRef
from modules.directory.services.sync import ensure_users_cached


@dataclass(frozen=True)
class UserDTO:
    user_id: int
    username: str
    display_name: str
    kind: str
    email: str = ""
    department: str = ""
    programme: str = ""
    discipline: str = ""
    batch_year: int | None = None


def _to_dto(r: UserRef) -> UserDTO:
    return UserDTO(
        user_id=r.user_id, username=r.username, display_name=r.display_name,
        kind=r.kind, email=r.email, department=r.department,
        programme=r.programme, discipline=r.discipline, batch_year=r.batch_year,
    )


def get_users(user_ids: Sequence[int]) -> dict[int, UserDTO]:
    """Batched. A missing id is simply absent from the mapping — a visible,
    testable case rather than a silent None three layers up."""
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}
    ensure_users_cached(ids)
    return {r.user_id: _to_dto(r) for r in UserRef.objects.filter(user_id__in=ids)}


def user_ids_in_discipline(discipline: str) -> list[int]:
    return list(
        UserRef.objects.filter(discipline=discipline, kind="student", is_active=True)
        .values_list("user_id", flat=True)
    )


def search(q: str = "", kind: str | None = None, limit: int = 25) -> list[UserDTO]:
    qs = UserRef.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(display_name__icontains=q)
    return [_to_dto(r) for r in qs.order_by("display_name")[:limit]]
