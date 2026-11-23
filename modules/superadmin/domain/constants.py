from __future__ import annotations

# User archival statuses
ARCHIVAL_STATUS_REVERSIBLE = "reversible"
ARCHIVAL_STATUS_RESTORED = "restored"
ARCHIVAL_STATUS_FINALIZED_PERMANENT = "finalized_permanent"

ALL_ARCHIVAL_STATUSES = frozenset(
    {
        ARCHIVAL_STATUS_REVERSIBLE,
        ARCHIVAL_STATUS_RESTORED,
        ARCHIVAL_STATUS_FINALIZED_PERMANENT,
    }
)

# Purge request statuses
PURGE_STATUS_PENDING_IT_HEAD = "pending_it_head"
PURGE_STATUS_APPROVED = "approved"
PURGE_STATUS_REJECTED = "rejected"
PURGE_STATUS_PURGED = "purged"
PURGE_STATUS_EXPIRED = "expired"

ALL_PURGE_STATUSES = frozenset(
    {
        PURGE_STATUS_PENDING_IT_HEAD,
        PURGE_STATUS_APPROVED,
        PURGE_STATUS_REJECTED,
        PURGE_STATUS_PURGED,
        PURGE_STATUS_EXPIRED,
    }
)

# Permitted configuration parameter keys whitelist (BR-SA-035)
CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS = "archival.reversibility_window_days"
CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS = "purge.approval_ttl_hours"
CONFIG_KEY_BULK_MAX_BATCH_SIZE = "bulk.max_batch_size"
CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS = "security.session_inactivity_timeout_mins"
CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD = "security.failed_login_alert_threshold"

PERMITTED_CONFIG_KEYS = frozenset(
    {
        CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS,
        CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS,
        CONFIG_KEY_BULK_MAX_BATCH_SIZE,
        CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS,
        CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD,
    }
)

# Hardcoded safe system fallback defaults when unseeded
DEFAULT_POLICY_VALUES: dict[str, str | int] = {
    CONFIG_KEY_REVERSIBILITY_WINDOW_DAYS: 30,
    CONFIG_KEY_PURGE_APPROVAL_TTL_HOURS: 72,
    CONFIG_KEY_BULK_MAX_BATCH_SIZE: 1000,
    CONFIG_KEY_SESSION_INACTIVITY_TIMEOUT_MINS: 30,
    CONFIG_KEY_FAILED_LOGIN_ALERT_THRESHOLD: 5,
}

# Audit actions
AUDIT_ACTION_USER_ARCHIVED = "archival.user.created"
AUDIT_ACTION_USER_RESTORED = "archival.user.restored"
AUDIT_ACTION_USER_FINALIZED = "archival.user.finalized"
AUDIT_ACTION_DATASET_ARCHIVED = "archival.dataset.created"
AUDIT_ACTION_DATASET_RESTORED = "archival.dataset.restored"
AUDIT_ACTION_PURGE_REQUESTED = "purge.requested"
AUDIT_ACTION_PURGE_APPROVED = "purge.approved"
AUDIT_ACTION_PURGE_REJECTED = "purge.rejected"
AUDIT_ACTION_PURGE_EXECUTED = "purge.executed"
AUDIT_ACTION_PURGE_EXPIRED = "purge.expired"
AUDIT_ACTION_POLICY_SUPERSEDED = "policy.superseded"

# Notification channels
NOTIF_CHANNEL_EMAIL = "email"
NOTIF_CHANNEL_SMS = "sms"
NOTIF_CHANNEL_PORTAL = "portal"
