"""Claim progression facts that do not need the database (OA-BR-42, OA-BR-52)."""

from __future__ import annotations

from collections.abc import Iterable

THESIS = "thesis"
TA = "ta"
SUPERVISOR_ROLES = (THESIS, TA)


def pending_roles(recorded: Iterable[str]) -> tuple[str, ...]:
    done = set(recorded)
    return tuple(r for r in SUPERVISOR_ROLES if r not in done)


def both_recorded(recorded: Iterable[str]) -> bool:
    return not pending_roles(recorded)
