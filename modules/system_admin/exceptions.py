"""Structured exception hierarchy for modules.system_admin."""


class SystemAdminError(Exception):
    """Base exception for all System Admin errors."""
    default_message = "An error occurred in the System Administrator module."
    code = "system_admin_error"

    def __init__(self, message=None, code=None, details=None):
        super().__init__(message or self.default_message)
        self.message = message or self.default_message
        self.code = code or self.code
        self.details = details or {}


class IdentityValidationError(SystemAdminError):
    code = "identity_validation_error"


class ImmutableFieldModificationError(SystemAdminError):
    code = "immutable_field_modification_error"


class RoleLifecycleError(SystemAdminError):
    code = "role_lifecycle_error"


class RoleConflictError(SystemAdminError):
    code = "role_conflict_error"


class SingularRoleOccupiedError(SystemAdminError):
    code = "singular_role_occupied"


class ArchivalEligibilityError(SystemAdminError):
    code = "archival_ineligible"


class ReversibilityExpiredError(SystemAdminError):
    code = "reversibility_expired"


class PurgeAuthorizationError(SystemAdminError):
    code = "purge_authorization_error"


class CriticalReauthRequiredError(SystemAdminError):
    code = "critical_reauth_required"


class DataIsolationViolationError(SystemAdminError):
    code = "data_isolation_violation"


class ConfigurationBoundaryViolationError(SystemAdminError):
    code = "config_boundary_violation"


class BulkOperationLimitExceededError(SystemAdminError):
    code = "bulk_limit_exceeded"
