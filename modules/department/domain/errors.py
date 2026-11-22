"""Plain exceptions the domain raises; services translate them to HTTP errors."""

from __future__ import annotations


class RuleViolation(Exception):
    """A business rule refused the change (422)."""

    def __init__(self, code: str, message: str, details: list | None = None):
        super().__init__(message)
        self.code, self.message, self.details = code, message, details or []


class InvalidTransition(Exception):
    """The table has no such move (409)."""

    def __init__(self, machine: str, frm: str, to: str):
        super().__init__(f"A {machine} cannot move from {frm!r} to {to!r}.")
        self.machine, self.frm, self.to = machine, frm, to


class ActorNotAllowed(Exception):
    """The move exists but not for this role (403)."""

    def __init__(self, machine: str, actor: str | None, frm: str, to: str):
        super().__init__(f"A {actor or 'user'} may not move a {machine} from {frm!r} to {to!r}.")
        self.machine, self.actor, self.frm, self.to = machine, actor, frm, to
