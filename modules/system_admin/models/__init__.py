"""Export all domain model aggregates for the system_admin module."""
from modules.system_admin.models.users import (
    BasicUser,
    UserProfile,
    UserStatusHistory,
)
from modules.system_admin.models.roles import (
    RoleDefinition,
    RoleAssignment,
    RoleAssignmentHistory,
    RoleHandoverLog,
)
from modules.system_admin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.system_admin.models.audit import (
    SuperAdminAuditLog,
    UserActivityLog,
)
from modules.system_admin.models.security import (
    SuperAdminSession,
    FailedLoginAttempt,
    TwoFactorCredential,
)
from modules.system_admin.models.config import (
    SystemParameter,
)
from modules.system_admin.models.notifications import (
    NotificationOutbox,
)

__all__ = [
    "BasicUser",
    "UserProfile",
    "UserStatusHistory",
    "RoleDefinition",
    "RoleAssignment",
    "RoleAssignmentHistory",
    "RoleHandoverLog",
    "ArchivedUserRecord",
    "HistoricalDataArchive",
    "PurgeRequest",
    "SuperAdminAuditLog",
    "UserActivityLog",
    "SuperAdminSession",
    "FailedLoginAttempt",
    "TwoFactorCredential",
    "SystemParameter",
    "NotificationOutbox",
]
