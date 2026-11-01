"""Framework-free refusals. Services translate these into HTTP-shaped errors."""
from __future__ import annotations


class RuleViolation(Exception):
    """A leave rule refused the change. `code` is what the API envelope reports."""

    def __init__(self, message: str, code: str = "rule_violation", details=None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = list(details or [])
