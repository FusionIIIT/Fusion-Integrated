"""directory's public surface. The ONLY thing other modules may import.

Plural by signature on purpose: there is no get_user(id), because a singular
lookup is what gets called inside a loop.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client
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


def get_employees() -> list[UserDTO]:
    """Everyone on the payroll: faculty and staff, not students.

    Leave, payroll and anything else that acts on employees needs the whole
    set rather than a page of it, so this is deliberately unpaginated and
    deliberately not the display search below.
    """
    return [
        _to_dto(r)
        for r in UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).order_by("user_id")
    ]


def held_employee_ids() -> set[int]:
    return set(
        UserRef.objects.filter(
            kind__in=("faculty", "staff"), is_active=True
        ).values_list("user_id", flat=True)
    )


def employee_projection_disagreement() -> tuple[list[int], list[int]] | None:
    """Where this service and the identity service disagree about the payroll.

    Returns (missing, stale): people the identity service calls employees and
    this one has not got, and people this one still calls employees and the
    identity service no longer does. **Both** matter. Checking only the first
    leaves a projection that has never dropped anybody -- someone reclassified
    upstream stays an employee here forever and keeps drawing entitlement.

    Compares identities, not counts. A count comparison passes whenever the two
    totals happen to agree, which is exactly the case this guard exists to
    catch: the right number of the wrong people.

    Returns None when the identity service cannot be reached -- a caller about
    to act on "all employees" must not read an unreachable directory as
    agreement.
    """
    held = held_employee_ids()
    try:
        known = {r.user_id for r in get_client().iter_employees()}
    except IamUnavailable:
        return None
    return sorted(known - held), sorted(held - known)


def search(q: str = "", kind: str | None = None, limit: int = 25) -> list[UserDTO]:
    qs = UserRef.objects.filter(is_active=True)
    if kind:
        qs = qs.filter(kind=kind)
    if q:
        qs = qs.filter(display_name__icontains=q)
    return [_to_dto(r) for r in qs.order_by("display_name")[:limit]]
