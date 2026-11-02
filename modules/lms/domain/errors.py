"""Domain exceptions for LMS (Course Management).

Pure Python exceptions with no DRF or framework dependencies.
"""


class LmsDomainError(Exception):
    """Base domain exception for LMS."""


class CourseAccessDenied(LmsDomainError):
    """Raised when a user attempts to access a course they are not enrolled/linked in (BR-LMS-001)."""


class ObserverAccessViolation(LmsDomainError):
    """Raised when an observer attempts to access student submissions or grades (BR-LMS-003)."""


class TAAuthoringRestriction(LmsDomainError):
    """Raised when a TA attempts to create/edit/delete assignments or materials (BR-LMS-004)."""


class InvalidMaterialState(LmsDomainError):
    """Raised when material visibility or scheduling constraints are violated (BR-LMS-005, BR-LMS-006)."""


class InvalidAssignmentState(LmsDomainError):
    """Raised when an operation is invalid for the assignment's current lifecycle state (BR-LMS-010)."""


class SubmissionTypeError(LmsDomainError):
    """Raised when submitted content does not match the configured submission type (BR-LMS-012)."""


class SubmissionClosedError(LmsDomainError):
    """Raised when submission is rejected due to deadline constraints (BR-LMS-013)."""


class SubmissionOwnershipError(LmsDomainError):
    """Raised when a student attempts to view or modify another student's submission (BR-LMS-014)."""


class UnauthorizedGradingError(LmsDomainError):
    """Raised when a user without grading authority attempts to grade or release (BR-LMS-015, BR-LMS-017)."""


class GradeNotReleasedError(LmsDomainError):
    """Raised when a student attempts to access unreleased draft grades (BR-LMS-016, BR-LMS-018)."""


class InvalidTransition(LmsDomainError):
    """Raised when an invalid state transition is attempted in an LMS workflow."""
