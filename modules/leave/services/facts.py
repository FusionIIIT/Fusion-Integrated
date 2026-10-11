"""Who the people in a request are, as IAM describes them.

ELM holds no user table, so an employee's kind (faculty or staff) and unit come
from the IAM directory. Batched by signature, like every other directory read
in this service, so eligibility for a list of requests is one call rather than
one per row.
"""
from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from fusion_auth.client import IamUnavailable, get_client

log = logging.getLogger("fusion.leave.facts")

FACULTY = "faculty"
STAFF = "staff"


@dataclass(frozen=True)
class Employee:
    user_id: int
    display_name: str = ""
    kind: str = STAFF
    unit: str = ""

    @property
    def is_employee(self) -> bool:
        return self.kind in (FACULTY, STAFF)


def employees(user_ids: Sequence[int]) -> dict[int, Employee]:
    """Directory data for a batch of ids. Unknown ids simply do not appear."""
    ids = sorted({int(i) for i in user_ids if i is not None})
    if not ids:
        return {}
    try:
        found = get_client().get_users(ids)
    except IamUnavailable as exc:
        # Fail closed: an unreachable directory must not read as "eligible".
        log.warning("leave.facts.iam_unavailable ids=%d err=%s", len(ids), exc)
        return {}
    return {
        uid: Employee(user_id=uid, display_name=ref.display_name,
                      kind=(ref.kind or STAFF).lower(),
                      unit=ref.department or ref.discipline or "")
        for uid, ref in found.items()
    }


def employee(user_id: int) -> Employee | None:
    return employees([user_id]).get(int(user_id))
