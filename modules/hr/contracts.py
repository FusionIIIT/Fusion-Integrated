"""hr's public surface — the ONLY thing other modules (e.g. leave) may import.

Plural by signature: `get_employments(user_ids)` not `get_employment(user_id)`.
This makes an N+1 query unwritable by design.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from modules.hr.models import EmploymentContract


@dataclass(frozen=True)
class EmploymentDTO:
    user_id: int
    is_employed: bool
    department_id: int | None
    department_name: str
    title: str
    kind: str   # permanent | temporary | contractual | intern


def get_employments(user_ids: Sequence[int]) -> dict[int, EmploymentDTO]:
    """Active employment record per user. Absent users get ``is_employed=False``.

    Leave consumes this. Neither module reads the other's tables.
    Plural by signature — an N+1 is unwritable.
    """
    ids = {int(i) for i in user_ids if i is not None}
    if not ids:
        return {}

    rows = (
        EmploymentContract.objects
        .filter(user_id__in=ids, status="active")
        .select_related("department")
        .values("user_id", "department_id", "department__name", "title", "kind")
    )
    found: dict[int, EmploymentDTO] = {}
    for r in rows:
        found[r["user_id"]] = EmploymentDTO(
            user_id=r["user_id"],
            is_employed=True,
            department_id=r["department_id"],
            department_name=r["department__name"] or "",
            title=r["title"],
            kind=r["kind"],
        )

    # Fill in the "not found" set so callers never have to handle KeyError.
    for uid in ids:
        if uid not in found:
            found[uid] = EmploymentDTO(
                user_id=uid, is_employed=False,
                department_id=None, department_name="",
                title="", kind="",
            )
    return found
