"""API views export for System Admin."""
from modules.system_admin.api.views.archive_views import (
    ArchiveDatasetView,
    ArchiveListView,
    ArchiveUserView,
    PurgeAuthorizeView,
    PurgeRequestView,
    RestoreUserView,
)
from modules.system_admin.api.views.audit_views import (
    AuditLogListView,
    FailedLoginListView,
)
from modules.system_admin.api.views.config_views import ConfigView
from modules.system_admin.api.views.dashboard_views import DashboardView
from modules.system_admin.api.views.role_views import (
    RoleAssignView,
    RoleExtendView,
    RoleListView,
    RoleReassignView,
    RoleRevokeView,
)
from modules.system_admin.api.views.user_views import (
    UserBulkCreateView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserStatusView,
)

__all__ = [
    "ArchiveDatasetView",
    "ArchiveListView",
    "ArchiveUserView",
    "AuditLogListView",
    "ConfigView",
    "DashboardView",
    "FailedLoginListView",
    "PurgeAuthorizeView",
    "PurgeRequestView",
    "RestoreUserView",
    "RoleAssignView",
    "RoleExtendView",
    "RoleListView",
    "RoleReassignView",
    "RoleRevokeView",
    "UserBulkCreateView",
    "UserCreateView",
    "UserDetailView",
    "UserListView",
    "UserStatusView",
]
