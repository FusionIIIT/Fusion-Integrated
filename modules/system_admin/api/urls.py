"""System Admin API URLs."""
from __future__ import annotations

from django.urls import path

from modules.system_admin.api.views import (
    ArchiveDatasetView,
    ArchiveListView,
    ArchiveUserView,
    AuditLogListView,
    ConfigView,
    DashboardView,
    FailedLoginListView,
    PurgeAuthorizeView,
    PurgeRequestView,
    RestoreUserView,
    RoleAssignView,
    RoleExtendView,
    RoleListView,
    RoleReassignView,
    RoleRevokeView,
    UserBulkCreateView,
    UserCreateView,
    UserDetailView,
    UserListView,
    UserStatusView,
)

urlpatterns = [
    # Dashboard
    path("dashboard/", DashboardView.as_view(), name="dashboard"),
    # User lifecycle
    path("users/", UserListView.as_view(), name="user_list"),
    path("users/create/", UserCreateView.as_view(), name="user_create"),
    path("users/bulk-create/", UserBulkCreateView.as_view(), name="user_bulk_create"),
    path("users/<int:user_id>/", UserDetailView.as_view(), name="user_detail"),
    path("users/<int:user_id>/status/", UserStatusView.as_view(), name="user_status"),
    # Roles
    path("roles/", RoleListView.as_view(), name="role_list"),
    path("roles/assign/", RoleAssignView.as_view(), name="role_assign"),
    path("roles/<int:role_id>/reassign/", RoleReassignView.as_view(), name="role_reassign"),
    path("roles/<int:role_id>/revoke/", RoleRevokeView.as_view(), name="role_revoke"),
    path("roles/<int:role_id>/extend/", RoleExtendView.as_view(), name="role_extend"),
    # Archives & Purge
    path("archives/", ArchiveListView.as_view(), name="archive_list"),
    path("archives/user/", ArchiveUserView.as_view(), name="archive_user"),
    path("archives/user/<int:user_id>/restore/", RestoreUserView.as_view(), name="restore_user"),
    path("archives/dataset/", ArchiveDatasetView.as_view(), name="archive_dataset"),
    path("archives/purge-request/", PurgeRequestView.as_view(), name="purge_request"),
    path(
        "archives/purge-request/<int:purge_id>/authorize/",
        PurgeAuthorizeView.as_view(),
        name="purge_authorize",
    ),
    # Audit
    path("audit/", AuditLogListView.as_view(), name="audit_list"),
    path("audit/failed-logins/", FailedLoginListView.as_view(), name="failed_login_list"),
    # Configuration
    path("config/", ConfigView.as_view(), name="config"),
    # Assignment 8 compatibility aliases
    path("users/alias/", UserListView.as_view(), name="sa-users"),
    path("users/<int:pk>/status/alias/", UserStatusView.as_view(), name="sa-user-status"),
    path("roles/assign/alias/", RoleAssignView.as_view(), name="sa-role-assign"),
    path("roles/<int:pk>/revoke/alias/", RoleRevokeView.as_view(), name="sa-role-revoke"),
    path("audit/alias/", AuditLogListView.as_view(), name="sa-audit-logs"),

]
