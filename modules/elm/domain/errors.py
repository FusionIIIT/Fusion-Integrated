"""Domain-level rule failures.

A service catches these and translates them into `ConflictError` / `BadRequest`
at the HTTP boundary, so `domain/` stays callable from a Celery task or a
management command where an HTTP status is noise.
"""
from __future__ import annotations


class RuleViolation(Exception):
    """A business rule (BR-EL-xxx) refused the operation."""

    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class InvalidTransition(RuleViolation):
    def __init__(self, frm: str, to: str):
        super().__init__(
            "invalid_transition",
            f"Cannot move a leave request from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(RuleViolation):
    def __init__(self, actor_role: str, frm: str, to: str):
        super().__init__(
            "actor_not_allowed",
            f"A {actor_role} may not move a leave request from {frm!r} to {to!r}.")
        self.actor_role, self.frm, self.to = actor_role, frm, to
