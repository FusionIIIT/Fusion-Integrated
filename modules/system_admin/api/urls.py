"""URL configuration for System Admin module."""
from django.urls import path

from .views import (
    ActiveRoleSwitchView,
    AdminDashboardView,
    ArchivedRecordListView,
    ArchivedUserListView,
    ArchiveHistoricalDataView,
    ArchiveUserActionView,
    AuditLogListView,
    AuditReportExportView,
    BulkUserCreateView,
    BulkUserStatusUpdateView,
    PurgeAuthorizeView,
    PurgeRequestListCreateView,
    RestoreHistoricalDataView,
    RestoreUserActionView,
    RoleAssignmentListCreateView,
    RoleDefinitionListView,
    RoleExtendView,
    RoleReassignView,
    RoleRevokeView,
    RoleVacanciesView,
    SuperAdminLoginView,
    SuperAdminLogoutView,
    SystemConfigView,
    UserDeactivateView,
    UserDetailView,
    UserListCreateView,
    UserReactivateView,
)

urlpatterns = [
    # Dashboard
    path("dashboard", AdminDashboardView.as_view(), name="system_admin_dashboard"),

    # Users
    path("users", UserListCreateView.as_view(), name="system_admin_users"),
    path("users/<int:user_id>", UserDetailView.as_view(), name="system_admin_user_detail"),
    path("users/<int:user_id>/deactivate", UserDeactivateView.as_view(), name="system_admin_user_deactivate"),
    path("users/<int:user_id>/reactivate", UserReactivateView.as_view(), name="system_admin_user_reactivate"),
    path("users/bulk-create", BulkUserCreateView.as_view(), name="system_admin_user_bulk_create"),
    path("users/bulk-status", BulkUserStatusUpdateView.as_view(), name="system_admin_user_bulk_status"),

    # Roles
    path("roles/definitions", RoleDefinitionListView.as_view(), name="system_admin_role_definitions"),
    path("roles/vacancies", RoleVacanciesView.as_view(), name="system_admin_role_vacancies"),
    path("roles/assignments", RoleAssignmentListCreateView.as_view(), name="system_admin_role_assignments"),
    path("roles/assignments/<int:assignment_id>/reassign", RoleReassignView.as_view(), name="system_admin_role_reassign"),
    path("roles/assignments/<int:assignment_id>/revoke", RoleRevokeView.as_view(), name="system_admin_role_revoke"),
    path("roles/assignments/<int:assignment_id>/extend", RoleExtendView.as_view(), name="system_admin_role_extend"),
    path("roles/switch-active", ActiveRoleSwitchView.as_view(), name="system_admin_role_switch_active"),

    # Archival & Purge
    path("archive/records", ArchivedRecordListView.as_view(), name="system_admin_archive_records"),
    path("archive/records/<int:archive_id>/restore", RestoreHistoricalDataView.as_view(), name="system_admin_archive_record_restore"),
    path("archive/users", ArchivedUserListView.as_view(), name="system_admin_archive_users"),
    path("archive/users/<int:user_id>/archive", ArchiveUserActionView.as_view(), name="system_admin_archive_user"),
    path("archive/users/<int:user_id>/restore", RestoreUserActionView.as_view(), name="system_admin_restore_user"),
    path("archive/historical-data", ArchiveHistoricalDataView.as_view(), name="system_admin_archive_historical_data"),
    path("archive/purge-requests", PurgeRequestListCreateView.as_view(), name="system_admin_purge_requests"),
    path("archive/purge-requests/<int:request_id>/authorize", PurgeAuthorizeView.as_view(), name="system_admin_purge_authorize"),

    # Audit & Monitoring
    path("audit/logs", AuditLogListView.as_view(), name="system_admin_audit_logs"),
    path("audit/export", AuditReportExportView.as_view(), name="system_admin_audit_export"),

    # Configuration
    path("config", SystemConfigView.as_view(), name="system_admin_config"),

    # Operator Authentication & Sessions
    path("auth/login", SuperAdminLoginView.as_view(), name="system_admin_auth_login"),
    path("auth/logout", SuperAdminLogoutView.as_view(), name="system_admin_auth_logout"),
]
