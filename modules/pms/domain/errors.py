"""Domain errors for the Patent Management System (PMS).

Pure Python: no Django or DRF imports.
"""

from __future__ import annotations


class PmsDomainError(Exception):
    """Base error for PMS domain violations."""

    code = "pms_domain_error"
    message = "A PMS domain rule was violated."

    def __init__(
        self, message: str | None = None, *, code: str | None = None, details: list | None = None
    ):
        super().__init__(message or self.message)
        self.message = message or self.message
        self.code = code or self.code
        self.details = details or []


class InvalidTransitionError(PmsDomainError):
    code = "invalid_transition"
    message = "The requested state transition is not allowed."


class ConflictOfInterestError(PmsDomainError):
    code = "conflict_of_interest"
    message = "Action rejected due to a conflict of interest."


class InsufficientJustificationError(PmsDomainError):
    code = "insufficient_justification"
    message = "Justification must be at least 50 characters."


class DeadlineExceededError(PmsDomainError):
    code = "deadline_exceeded"
    message = "The permitted deadline for this action has expired."


class BudgetThresholdExceededError(PmsDomainError):
    code = "budget_threshold_exceeded"
    message = "Total cost exceeds the configured threshold limit and requires escalation."


class IncompleteInventorsError(PmsDomainError):
    code = "incomplete_inventors"
    message = "Inventor agreements and ownership shares must be valid and complete."


class InvalidDocumentError(PmsDomainError):
    code = "invalid_document"
    message = "Document must be a malware-free PDF under 50 MB."


class UnauthorizedRoleError(PmsDomainError):
    code = "unauthorized_role"
    message = "The active role is not authorized for this patent action."


class PreconditionNotMetError(PmsDomainError):
    code = "precondition_not_met"
    message = "Lifecycle preconditions for this action are not satisfied."


class WithdrawalNotAllowedError(PmsDomainError):
    code = "withdrawal_not_allowed"
    message = "Withdrawal is not permitted for the current application state or missing required reason/consent."


class AppealNotAllowedError(PmsDomainError):
    code = "appeal_not_allowed"
    message = (
        "Appeals may only be filed for Rejected applications within the allowed appeal period."
    )
