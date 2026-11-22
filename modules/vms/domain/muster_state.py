"""Emergency muster lifecycle (pure Python): open -> closed. CFR-018."""
from __future__ import annotations

OPEN, CLOSED = "open", "closed"
STATES = (OPEN, CLOSED)
CLOSE = "close"
TERMINAL = frozenset({CLOSED})

TABLE = {(OPEN, CLOSE): CLOSED}

#: Entry statuses: unaccounted -> accounted | evacuated
UNACCOUNTED, ACCOUNTED, EVACUATED = "unaccounted", "accounted", "evacuated"
MARK_ACCOUNTED, MARK_EVACUATED = "mark_accounted", "mark_evacuated"
ENTRY_TABLE = {
    (UNACCOUNTED, MARK_ACCOUNTED): ACCOUNTED,
    (UNACCOUNTED, MARK_EVACUATED): EVACUATED,
}


class InvalidTransition(Exception):
    def __init__(self, frm: str, event: str):
        super().__init__(f"No {event!r} move from {frm!r}.")
        self.frm, self.event = frm, event


def resolve(frm: str, event: str) -> str:
    try:
        return TABLE[(frm, event)]
    except KeyError:
        raise InvalidTransition(frm, event) from None


def resolve_entry(frm: str, event: str) -> str:
    try:
        return ENTRY_TABLE[(frm, event)]
    except KeyError:
        raise InvalidTransition(frm, event) from None
