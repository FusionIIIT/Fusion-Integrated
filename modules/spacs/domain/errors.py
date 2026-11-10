"""Domain-level exceptions for Awards and Scholarships (SPACS). Pure Python."""


class SpacsDomainError(Exception):
    """Base exception for all SPACS domain-rule violations."""


class EligibilityError(SpacsDomainError):
    """Raised when machine-checkable or manual eligibility criteria fail (BR-SPACS-001)."""


class DuplicateApplicationError(SpacsDomainError):
    """Raised when an active/submitted duplicate application exists (BR-SPACS-002)."""


class DocumentReuseError(SpacsDomainError):
    """Raised when document reuse fails validity or ownership constraints (BR-SPACS-003)."""


class CompletenessError(SpacsDomainError):
    """Raised when mandatory fields or required documents are missing (BR-SPACS-004)."""


class UnauthorizedActionError(SpacsDomainError):
    """Raised when an actor attempts an action outside their role or ownership (BR-SPACS-005, 006, 010, 018)."""


class InvalidTransitionError(SpacsDomainError):
    """Raised when a state transition is not allowed by the workflow state machine."""


class RenewalEligibilityError(SpacsDomainError):
    """Raised when scholarship renewal criteria or windows are not met (BR-SPACS-017)."""


class AwardPolicyError(SpacsDomainError):
    """Raised when award cycle, candidate, or publication prerequisites fail (BR-SPACS-019, 020, 023)."""


class AuditProtectionError(SpacsDomainError):
    """Raised when an unauthorized attempt is made to alter or delete an audit log (BR-SPACS-021)."""
