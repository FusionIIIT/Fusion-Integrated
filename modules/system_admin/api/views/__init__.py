"""System Admin views package."""

from .archival import (
    ArchivedRecordListView,
    ArchivedUserListView,
    ArchiveHistoricalDataView,
    ArchiveUserActionView,
    PurgeAuthorizeView,
    PurgeRequestListCreateView,
    RestoreHistoricalDataView,
    RestoreUserActionView,
)
from .audit import (
    AdminDashboardView,
    AuditLogListView,
    AuditReportExportView,
)
from .auth import SuperAdminLoginView, SuperAdminLogoutView
from .config import SystemConfigView
from .roles import (
    ActiveRoleSwitchView,
    RoleAssignmentListCreateView,
    RoleDefinitionListView,
    RoleExtendView,
    RoleReassignView,
    RoleRevokeView,
    RoleVacanciesView,
)
from .users import (
    BulkUserCreateView,
    BulkUserStatusUpdateView,
    UserDeactivateView,
    UserDetailView,
    UserListCreateView,
    UserReactivateView,
)

__all__ = [
    "ActiveRoleSwitchView",
    "AdminDashboardView",
    "ArchiveHistoricalDataView",
    "ArchiveUserActionView",
    "ArchivedRecordListView",
    "ArchivedUserListView",
    "AuditLogListView",
    "AuditReportExportView",
    "BulkUserCreateView",
    "BulkUserStatusUpdateView",
    "PurgeAuthorizeView",
    "PurgeRequestListCreateView",
    "RestoreHistoricalDataView",
    "RestoreUserActionView",
    "RoleAssignmentListCreateView",
    "RoleDefinitionListView",
    "RoleExtendView",
    "RoleReassignView",
    "RoleRevokeView",
    "RoleVacanciesView",
    "SuperAdminLoginView",
    "SuperAdminLogoutView",
    "SystemConfigView",
    "UserDeactivateView",
    "UserDetailView",
    "UserListCreateView",
    "UserReactivateView",
]
