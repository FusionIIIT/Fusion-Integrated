"""Central definitions, enums, TextChoices, and policy defaults for system_admin."""
from django.db import models


class UserKind(models.TextChoices):
    STUDENT = "student", "Student"
    FACULTY = "faculty", "Faculty"
    STAFF = "staff", "Staff"


class UserLifecycleStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    DEACTIVATED = "deactivated", "Deactivated"
    ARCHIVED = "archived", "Archived"


class RoleCategory(models.TextChoices):
    BASIC = "basic", "Basic Role"
    RANK = "rank", "Academic Rank"
    OFFICE = "office", "Administrative Office"
    FUNCTIONAL = "functional", "Functional Role"


class RoleAssignmentState(models.TextChoices):
    SCHEDULED = "scheduled", "Scheduled"
    ACTIVE = "active", "Active"
    EXTENDED = "extended", "Extended"
    EXPIRED = "expired", "Expired"
    REVOKED = "revoked", "Revoked"


class RoleRevocationType(models.TextChoices):
    STANDARD = "standard", "Standard Revocation (>= 1 day notice)"
    EMERGENCY = "emergency", "Emergency Revocation (Immediate)"
    AUTOMATIC = "automatic", "Automatic Revocation (Deactivation / Expiry)"


class PendingTaskDisposition(models.TextChoices):
    TRANSFER = "transfer", "Transfer Pending Tasks"
    CLOSE = "close", "Close Pending Tasks"


class UserArchivalStatus(models.TextChoices):
    REVERSIBLE = "reversible", "Archived — Reversible Window Open"
    PERMANENT_NON_RESTORABLE = "permanent_non_restorable", "Archived — Permanently Non-Restorable"
    RESTORED = "restored", "Restored to Active"


class PurgeRequestStatus(models.TextChoices):
    PENDING_IT_HEAD = "pending_it_head", "Pending IT Head Authorization"
    APPROVED = "approved", "Approved by IT Head"
    REJECTED = "rejected", "Rejected by IT Head"
    PURGED = "purged", "Permanently Purged"


class AuditAction(models.TextChoices):
    USER_CREATE = "user.create", "Create Basic User"
    USER_UPDATE = "user.update", "Update Basic User Profile"
    USER_DEACTIVATE = "user.deactivate", "Deactivate User"
    USER_REACTIVATE = "user.reactivate", "Reactivate User"
    USER_BULK_CREATE = "user.bulk_create", "Bulk Create Users"
    USER_BULK_STATUS = "user.bulk_status", "Bulk User Status Update"
    ROLE_ASSIGN = "role.assign", "Assign Additional Role"
    ROLE_REASSIGN = "role.reassign", "Reassign Role"
    ROLE_REVOKE = "role.revoke", "Revoke Role"
    ROLE_EXTEND = "role.extend", "Extend Role Validity"
    ROLE_SWITCH = "role.switch", "Switch Active Role"
    ARCHIVE_USER = "archive.user", "Archive User Account"
    RESTORE_USER = "archive.user_restore", "Restore Archived User"
    FINALIZE_USER_ARCHIVE = "archive.user_finalize", "Finalize User as Non-Restorable"
    ARCHIVE_DATA = "archive.data", "Archive Historical Data"
    RESTORE_DATA = "archive.data_restore", "Restore Historical Data"
    PURGE_REQUEST = "purge.request", "Request Permanent Purge"
    PURGE_AUTHORIZE = "purge.authorize", "Authorize/Reject Permanent Purge"
    CONFIG_UPDATE = "config.update", "Update Permitted System Parameter"
    AUTH_LOGIN = "auth.login", "Super Admin Login"
    AUTH_LOGOUT = "auth.logout", "Super Admin Logout"
    AUTH_FAILED = "auth.failed", "Failed Super Admin Login"
    AUTH_SESSION_TERMINATE = "auth.session_terminate", "Inactivity Session Terminated"
    SECURITY_ALERT = "security.alert", "Failed Login Threshold Alert"


class AuditResult(models.TextChoices):
    SUCCESS = "success", "Success"
    FAILURE = "failure", "Failure"
    DENIED = "denied", "Denied / Blocked"


class NotificationChannel(models.TextChoices):
    EMAIL = "email", "Email"
    IN_APP = "in_app", "In-App Notification"
    SMS = "sms", "SMS (Optional for Security Alerts)"


class NotificationStatus(models.TextChoices):
    PENDING = "pending", "Pending Delivery"
    SENT = "sent", "Successfully Sent"
    FAILED = "failed", "Delivery Failed"


class PermittedConfigKey:
    """Whitelisted system parameters allowed under BR-SA-035."""
    PASSWORD_MIN_LENGTH = "password.min_length"
    PASSWORD_COMPLEXITY_REQUIRED = "password.complexity_required"
    PASSWORD_ROTATION_DAYS = "password.rotation_days"
    SESSION_INACTIVITY_TIMEOUT_MINUTES = "session.inactivity_timeout_minutes"
    ARCHIVAL_MIN_DEACTIVATION_DAYS = "archival.min_deactivation_days"
    ARCHIVAL_REVERSIBLE_WINDOW_DAYS = "archival.reversible_window_days"
    ARCHIVAL_HISTORICAL_RETENTION_YEARS = "archival.historical_retention_years"
    ROLE_EXPIRY_REMINDER_LEAD_DAYS = "role.expiry_reminder_lead_days"
    ROLE_PREVIOUS_HOLDER_AUDIT_DAYS = "role.previous_holder_audit_days"
    NOTIFICATION_ENABLE_SMS_ALERTS = "notification.enable_sms_alerts"
    BULK_OPERATION_MAX_RECORDS = "bulk.max_records"

    ALL_KEYS = frozenset({
        PASSWORD_MIN_LENGTH,
        PASSWORD_COMPLEXITY_REQUIRED,
        PASSWORD_ROTATION_DAYS,
        SESSION_INACTIVITY_TIMEOUT_MINUTES,
        ARCHIVAL_MIN_DEACTIVATION_DAYS,
        ARCHIVAL_REVERSIBLE_WINDOW_DAYS,
        ARCHIVAL_HISTORICAL_RETENTION_YEARS,
        ROLE_EXPIRY_REMINDER_LEAD_DAYS,
        ROLE_PREVIOUS_HOLDER_AUDIT_DAYS,
        NOTIFICATION_ENABLE_SMS_ALERTS,
        BULK_OPERATION_MAX_RECORDS,
    })
