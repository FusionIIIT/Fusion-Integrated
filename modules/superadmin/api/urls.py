"""URL routing for Super Admin API."""

from django.urls import path

from modules.superadmin.api.views import (
    ArchiveExportView,
    ArchiveListView,
    ArchiveRestoreView,
    AuditLogExportView,
    AuditLogListView,
    BulkUserCreateView,
    BulkUserStatusView,
    DashboardMetricsView,
    PurgeAuthorizeView,
    PurgeRequestListView,
    RoleExtendView,
    RoleListView,
    RoleReassignView,
    RoleRevokeView,
    SystemParameterListView,
    UserArchiveView,
    UserDeactivateView,
    UserDetailView,
    UserExportView,
    UserListView,
    UserReactivateView,
    UserRestoreView,
)

app_name = "superadmin"

urlpatterns = [
    # Dashboard & Users
    path("dashboard/", DashboardMetricsView.as_view(), name="dashboard"),
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/export/", UserExportView.as_view(), name="user_export"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user_detail"),
    path("users/<int:user_id>/deactivate/", UserDeactivateView.as_view(), name="user_deactivate"),
    path("users/<int:user_id>/reactivate/", UserReactivateView.as_view(), name="user_reactivate"),
    path("users/<int:user_id>/archive/", UserArchiveView.as_view(), name="user_archive"),
    path("users/<int:user_id>/restore/", UserRestoreView.as_view(), name="user_restore"),
    path("users/bulk-create/", BulkUserCreateView.as_view(), name="bulk_create"),
    path("users/bulk-status/", BulkUserStatusView.as_view(), name="bulk_status"),
    # Roles
    path("roles/", RoleListView.as_view(), name="role_list"),
    path("roles/<int:assignment_id>/extend/", RoleExtendView.as_view(), name="role_extend"),
    path("roles/<int:assignment_id>/revoke/", RoleRevokeView.as_view(), name="role_revoke"),
    path("roles/<int:assignment_id>/reassign/", RoleReassignView.as_view(), name="role_reassign"),
    # Archive & Purge
    path("archive/", ArchiveListView.as_view(), name="archive_list"),
    path("archive/export/", ArchiveExportView.as_view(), name="archive_export"),
    path("archive/<int:archive_id>/restore/", ArchiveRestoreView.as_view(), name="archive_restore"),
    path("purge/requests/", PurgeRequestListView.as_view(), name="purge_requests"),
    path(
        "purge/requests/<int:request_id>/authorize/",
        PurgeAuthorizeView.as_view(),
        name="purge_authorize",
    ),
    # Audit & System Policy
    path("audit/", AuditLogListView.as_view(), name="audit_logs"),
    path("audit/export/", AuditLogExportView.as_view(), name="audit_export"),
    path("config/", SystemParameterListView.as_view(), name="system_config"),
]
