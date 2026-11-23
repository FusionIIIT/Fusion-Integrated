"""Refusals raised by the rules; the service layer turns them into HTTP-aware errors."""
from __future__ import annotations


class PmsRuleError(Exception):
    """A rule refused the request. `code` is stable; the message is written for a person."""

    kind = "conflict"

    def __init__(self, message: str, *, code: str):
        super().__init__(message)
        self.message = message
        self.code = code


class RuleViolation(PmsRuleError):
    """Well-formed, but the record's current state or a policy forbids it."""

    kind = "conflict"


class InvalidInput(PmsRuleError):
    """The submitted content itself fails a rule."""

    kind = "invalid"


class InvalidTransition(RuleViolation):
    def __init__(self, machine: str, frm: str, event: str):
        super().__init__(
            f"This {machine.replace('_', ' ')} is {frm.replace('_', ' ')}, so "
            f"'{event.replace('_', ' ')}' is not possible now. Refresh to see its current state.",
            code="invalid_transition")
        self.machine, self.frm, self.event = machine, frm, event


class ActorNotAllowed(RuleViolation):
    def __init__(self, machine: str, frm: str, event: str, actor: str):
        super().__init__(
            f"Your role cannot '{event.replace('_', ' ')}' a {machine.replace('_', ' ')} "
            f"that is {frm.replace('_', ' ')}.",
            code="actor_not_allowed")
        self.machine, self.frm, self.event, self.actor = machine, frm, event, actor
