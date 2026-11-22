"""Domain exceptions for System Admin (pure Python, zero framework imports)."""


class SystemAdminDomainError(Exception):
    """Base exception for all system admin domain violations."""


class DomainValidationError(SystemAdminDomainError):
    """Raised when basic domain validation rules fail."""


class InstituteIdImmutableError(SystemAdminDomainError):
    """Raised when an attempt is made to alter an immutable Institute ID (BR-SA-001)."""


class InvalidEmailDomainError(DomainValidationError):
    """Raised when email is not a valid institute email (BR-SA-002)."""


class IneligibleUserTypeError(DomainValidationError):
    """Raised when user type is ineligible for a role or missing data (BR-SA-003, BR-SA-010)."""


class InvalidDateRangeError(DomainValidationError):
    """Raised when role start date is after end date or missing mandatory dates (BR-SA-008)."""


class SingularRoleOccupancyError(SystemAdminDomainError):
    """Raised when attempting to assign a singular role to a second active holder (BR-SA-007)."""


class SeparationOfDutiesConflictError(SystemAdminDomainError):
    """Raised when assigning roles that violate SOD conflict policy (BR-SA-011)."""


class UserNotEligibleForArchivalError(SystemAdminDomainError):
    """Raised when archival eligibility rules are violated (BR-SA-004)."""


class ArchivalReversibilityExpiredError(SystemAdminDomainError):
    """Raised when restoration is attempted on a permanently archived user (BR-SA-005)."""


class RetentionNotElapsedError(SystemAdminDomainError):
    """Raised when permanent purge is attempted before retention period elapses (BR-SA-021)."""


class DualAuthorizationRequiredError(SystemAdminDomainError):
    """Raised when permanent purge lacks dual authorization (BR-SA-022)."""


PurgeDualAuthError = DualAuthorizationRequiredError


class DuplicateUserError(SystemAdminDomainError):
    """Raised when creating a user with already existing institute_id or username."""


class UserNotFoundError(SystemAdminDomainError):
    """Raised when a user account cannot be found."""


class RoleAssignmentNotFoundError(SystemAdminDomainError):
    """Raised when a role assignment cannot be found."""


class InvalidStateTransitionError(SystemAdminDomainError):
    """Raised when an illegal lifecycle state transition is requested."""


class ParameterOutOfBoundsError(DomainValidationError):
    """Raised when system configuration values exceed institutional policy bounds (BR-SA-035)."""
