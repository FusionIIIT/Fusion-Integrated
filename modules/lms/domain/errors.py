"""Pure domain errors for LMS Course Management."""
from __future__ import annotations


class LMSRuleError(ValueError):
    """Base exception for all LMS domain rule violations."""


class CourseAccessDeniedError(LMSRuleError):
    """Raised when an unlinked or unauthorized user attempts course workspace access."""


class CourseEditingDeniedError(LMSRuleError):
    """Raised when a non-faculty or unassigned user attempts course workspace edits."""


class MaterialAccessDeniedError(LMSRuleError):
    """Raised when an unauthorized user attempts to view or download a material."""


class MaterialAuthoringDeniedError(LMSRuleError):
    """Raised when a non-faculty user (TA, Student, Observer) attempts to author material."""


class AssignmentAccessDeniedError(LMSRuleError):
    """Raised when an unauthorized user attempts to view an assignment."""


class AssignmentAuthoringDeniedError(LMSRuleError):
    """Raised when a non-faculty user (TA, Student, Observer) attempts to author an assignment."""


class DeadlineWindowError(LMSRuleError):
    """Raised when submission window configuration violates deadline rules."""


class ExtensionDeniedError(LMSRuleError):
    """Raised when an extension request is unauthorized or invalid."""


class ExtensionNotFoundError(LMSRuleError):
    """Raised when a specified extension record does not exist."""


class SubmissionError(LMSRuleError):
    """Base exception for submission rule violations."""


class SubmissionTypeError(SubmissionError):
    """Raised when submission type is invalid or incompatible with assignment configuration."""


class SubmissionWindowClosedError(SubmissionError):
    """Raised when submission is attempted outside the allowable submission window."""


class SubmissionAccessDeniedError(SubmissionError):
    """Raised when an unauthorized user attempts to view or download a submission."""
