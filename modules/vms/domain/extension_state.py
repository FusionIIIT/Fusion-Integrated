"""Visit-extension request lifecycle (pure Python): pending -> approved | rejected. BR-194."""
from __future__ import annotations

PENDING, APPROVED, REJECTED = "pending", "approved", "rejected"
STATES = (PENDING, APPROVED, REJECTED)
TERMINAL = frozenset({APPROVED, REJECTED})
APPROVE, REJECT = "approve", "reject"

TABLE = {(PENDING, APPROVE): APPROVED, (PENDING, REJECT): REJECTED}


class InvalidTransition(Exception):
    def __init__(self, frm: str, event: str):
        super().__init__(f"No {event!r} move from {frm!r}.")
        self.frm, self.event = frm, event


def resolve(frm: str, event: str) -> str:
    try:
        return TABLE[(frm, event)]
    except KeyError:
        raise InvalidTransition(frm, event) from None
