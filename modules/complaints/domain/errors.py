"""Domain exceptions for Complaint Management System.

Framework-free refusals. Services translate these into domain/API error envelopes.
"""
from __future__ import annotations


class RuleViolation(Exception):
    """A business rule or workflow guard refused the operation."""

    def __init__(self, message: str, code: str = "rule_violation", details: list | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = list(details or [])


class InvalidTransition(RuleViolation):
    """An illegal lifecycle transition was attempted."""

    def __init__(self, from_status: str, to_status: str, reason: str = ""):
        msg = f"Cannot transition complaint from '{from_status}' to '{to_status}'."
        if reason:
            msg += f" {reason}"
        super().__init__(msg, code="invalid_transition")
        self.from_status = from_status
        self.to_status = to_status


class PermissionDenied(RuleViolation):
    """Caller does not hold the required permission."""

    def __init__(self, permission: str, message: str = ""):
        msg = message or f"Missing required permission '{permission}'."
        super().__init__(msg, code="permission_denied")
        self.permission = permission


class MandatoryFieldMissing(RuleViolation):
    """A required field was missing from the complaint payload."""

    def __init__(self, field_name: str):
        super().__init__(
            f"Mandatory complaint field '{field_name}' is required.",
            code="mandatory_field_missing",
        )
        self.field_name = field_name


class AttachmentConstraintError(RuleViolation):
    """Attachment failed file size or allowed type constraint."""

    def __init__(self, message: str):
        super().__init__(message, code="attachment_constraint_violated")


class RoleCardinalityError(RuleViolation):
    """Cardinality violation for CMS operational or supervisory roles."""

    def __init__(self, role_name: str, message: str = ""):
        msg = message or f"Exactly one active '{role_name}' is permitted at a time."
        super().__init__(msg, code="role_cardinality_violation")
        self.role_name = role_name


class ReopeningNotAllowed(RuleViolation):
    """Reopening is not eligible for this complaint."""

    def __init__(self, message: str):
        super().__init__(message, code="reopening_not_allowed")


class FeedbackNotAllowed(RuleViolation):
    """Feedback is not eligible for this complaint."""

    def __init__(self, message: str):
        super().__init__(message, code="feedback_not_allowed")


class EscalationNotAllowed(RuleViolation):
    """Complaint is not eligible for escalation."""

    def __init__(self, message: str):
        super().__init__(message, code="escalation_not_allowed")
