"""Domain exceptions for LMS (Course Management).

Pure Python exceptions with no DRF or framework dependencies.
"""


class LmsDomainError(Exception):
    """Base domain exception for LMS."""


class CourseAccessDenied(LmsDomainError):
    """Raised when a user attempts to access an un-enrolled course (BR-LMS-001)."""


class ObserverAccessViolation(LmsDomainError):
    """Raised when an observer attempts to access student submissions or grades (BR-LMS-003)."""


class TAAuthoringRestriction(LmsDomainError):
    """Raised when a TA attempts to author assignments or materials (BR-LMS-004)."""


class InvalidMaterialState(LmsDomainError):
    """Raised when material constraints are violated (BR-LMS-005, BR-LMS-006)."""


class InvalidAssignmentState(LmsDomainError):
    """Raised when operation is invalid for current lifecycle state (BR-LMS-010)."""


class SubmissionTypeError(LmsDomainError):
    """Raised when submitted content does not match the configured type (BR-LMS-012)."""


class SubmissionClosedError(LmsDomainError):
    """Raised when submission is rejected due to deadline constraints (BR-LMS-013)."""


class SubmissionOwnershipError(LmsDomainError):
    """Raised when accessing another student's submission (BR-LMS-014)."""


class UnauthorizedGradingError(LmsDomainError):
    """Raised when grading without authority (BR-LMS-015, BR-LMS-017)."""


class GradeNotReleasedError(LmsDomainError):
    """Raised when a student attempts to access unreleased draft grades (BR-LMS-016, BR-LMS-018)."""


class InvalidTransition(LmsDomainError):
    """Raised when an invalid state transition is attempted in an LMS workflow."""
