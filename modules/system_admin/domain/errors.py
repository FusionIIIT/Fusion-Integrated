"""Pure Python domain errors for System Admin module.

Zero Django / DRF imports. Inherits standard Exception so domain logic stays
portable and testable without a database.
"""


class SystemAdminDomainError(Exception):
    """Base class for all system admin domain errors."""

    def __init__(self, message: str, code: str = "domain_error", details: list | None = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or []


SuperAdminDomainError = SystemAdminDomainError


# User lifecycle & identity errors
class InstituteIdImmutableError(SystemAdminDomainError):
    """BR-SA-001: Institute ID cannot be changed once created."""
    def __init__(self, message: str = "Institute ID is immutable and cannot be changed."):
        super().__init__(message, code="institute_id_immutable")


class DuplicateInstituteIdError(SystemAdminDomainError):
    """BR-SA-001: Institute ID must be unique across Fusion."""
    def __init__(self, message: str = "Institute ID already exists."):
        super().__init__(message, code="duplicate_institute_id")


class InvalidInstituteEmailError(SystemAdminDomainError):
    """BR-SA-002: Only valid institute email address accepted."""
    def __init__(self, message: str = "Email must be a valid institute email address."):
        super().__init__(message, code="invalid_institute_email")


class MissingUserTypeDataError(SystemAdminDomainError):
    """BR-SA-003: User type required data validation error."""
    def __init__(self, message: str, missing_fields: list[str] | None = None):
        super().__init__(message, code="missing_user_type_data", details=missing_fields or [])
        self.missing_fields = missing_fields or []


class UserArchivalIneligibleError(SystemAdminDomainError):
    """BR-SA-004: User must be deactivated for the minimum interval and have no pending transactions."""
    def __init__(self, message: str = "User is not eligible for archival."):
        super().__init__(message, code="user_archival_ineligible")


class ArchivedUserPermanentError(SystemAdminDomainError):
    """BR-SA-005, ISS-SA-004: Archived user is permanently non-restorable after reversible window."""
    def __init__(self, message: str = "Archived user account is permanently non-restorable."):
        super().__init__(message, code="archived_user_permanent_non_restorable")


# Role management errors
class SingularRoleOccupancyError(SystemAdminDomainError):
    """BR-SA-007: Singular role cannot have more than one active holder for the same scope."""
    def __init__(self, message: str = "Singular role already has an active holder for this scope."):
        super().__init__(message, code="singular_role_occupied")


class InvalidRoleDatesError(SystemAdminDomainError):
    """BR-SA-008: Role start date is mandatory; end date required for time-bound roles."""
    def __init__(self, message: str = "Invalid role start or end dates."):
        super().__init__(message, code="invalid_role_dates")


class RoleIncompatibleUserTypeError(SystemAdminDomainError):
    """BR-SA-010: Role cannot be assigned to incompatible basic user type."""
    def __init__(self, message: str = "Role is incompatible with the user's basic type."):
        super().__init__(message, code="role_user_type_incompatible")


class RoleConflictError(SystemAdminDomainError):
    """BR-SA-011: Configured role conflict detected."""
    def __init__(self, message: str = "Role conflicts with currently assigned or incompatible roles."):
        super().__init__(message, code="role_conflict")


class InvalidNoticePeriodError(SystemAdminDomainError):
    """BR-SA-014: Standard revocation requires at least one day notice."""
    def __init__(self, message: str = "Standard role revocation requires at least 1 day advance notice."):
        super().__init__(message, code="invalid_notice_period")


class HistoricalDataArchivalIneligibleError(SystemAdminDomainError):
    """BR-SA-017: Historical data does not meet retention age or has pending actions."""
    def __init__(self, message: str = "Historical data is not eligible for archival."):
        super().__init__(message, code="historical_data_ineligible")


class AuditLogArchivalProhibitedError(SystemAdminDomainError):
    """BR-SA-017, BR-SA-025: Audit logs are permanently retained and cannot be archived or purged."""
    def __init__(self, message: str = "Audit logs cannot be archived or purged; permanent retention is required."):
        super().__init__(message, code="audit_log_archival_prohibited")


class PurgeRetentionNotElapsedError(SystemAdminDomainError):
    """BR-SA-021: Permanent purge requested before retention period elapsed."""
    def __init__(self, message: str = "Data cannot be purged before retention period has elapsed."):
        super().__init__(message, code="purge_retention_not_elapsed")


class DualAuthorizationRequiredError(SystemAdminDomainError):
    """BR-SA-022: Permanent purge requires dual authorization by Super Admin and IT Head."""
    def __init__(self, message: str = "Permanent purge requires dual authorization from IT Head."):
        super().__init__(message, code="dual_authorization_required")


class OperationalContentAccessForbiddenError(SystemAdminDomainError):
    """BR-SA-026: Super Admin forbidden from accessing operational content."""
    def __init__(self, message: str = "Access to operational module content is forbidden for Super Admin."):
        super().__init__(message, code="operational_content_forbidden")


class SuperAdminSelfModificationForbiddenError(SystemAdminDomainError):
    """BR-SA-028: Super Admin cannot self-assign or modify own Super Admin status."""
    def __init__(self, message: str = "Super Admin cannot assign or modify their own Super Admin status."):
        super().__init__(message, code="super_admin_self_modification_forbidden")


class CriticalOperationReauthRequiredError(SystemAdminDomainError):
    """BR-SA-029: Confirmation with reauthentication required for critical operations."""
    def __init__(self, message: str = "Critical operation requires authenticated confirmation."):
        super().__init__(message, code="critical_operation_reauth_required")


class BulkLimitExceededError(SystemAdminDomainError):
    """BR-SA-030: Bulk operations are capped at 1000 records."""
    def __init__(self, message: str = "Bulk operation exceeds maximum limit of 1000 records."):
        super().__init__(message, code="bulk_limit_exceeded")


class PermittedConfigBoundaryError(SystemAdminDomainError):
    """BR-SA-035: Only permitted system parameters may be configured."""
    def __init__(self, message: str = "Configuration parameter is outside the Super Admin control boundary."):
        super().__init__(message, code="permitted_config_boundary_violation")


class ActiveRoleInvalidError(SystemAdminDomainError):
    """BR-SA-034: Selected active role must be currently assigned and active."""
    def __init__(self, message: str = "Selected role is not active or not assigned to the user."):
        super().__init__(message, code="active_role_invalid")
