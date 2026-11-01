"""URL Routing for System Admin Module."""
from django.urls import path
from modules.systemadmin.api import views

urlpatterns = [
    # Dashboard
    path("dashboard/", views.DashboardOverviewView.as_view(), name="dashboard-overview"),

    # User Management
    path("users/", views.UserListView.as_view(), name="user-list"),
    path("users/create/", views.UserCreateView.as_view(), name="user-create"),
    path("users/<int:user_id>/", views.UserDetailView.as_view(), name="user-detail"),
    path("users/<int:user_id>/status/", views.UserStatusView.as_view(), name="user-status"),
    path("users/bulk-create/", views.UserBulkCreateView.as_view(), name="user-bulk-create"),
    path("users/bulk-status/", views.UserBulkStatusView.as_view(), name="user-bulk-status"),

    # Role Management
    path("roles/", views.RoleListView.as_view(), name="role-list"),
    path("roles/<int:role_id>/", views.RoleDetailView.as_view(), name="role-detail"),
    path("assignments/", views.RoleAssignmentListView.as_view(), name="assignment-list"),
    path("assignments/create/", views.RoleAssignView.as_view(), name="assignment-create"),
    path("assignments/<int:assignment_id>/reassign/", views.RoleReassignView.as_view(), name="assignment-reassign"),
    path("assignments/<int:assignment_id>/revoke/", views.RoleRevokeView.as_view(), name="assignment-revoke"),
    path("assignments/<int:assignment_id>/extend/", views.RoleExtendView.as_view(), name="assignment-extend"),

    # Archival & Purge
    path("archival/users/", views.ArchivedUserListView.as_view(), name="archived-user-list"),
    path("archival/users/create/", views.ArchiveUserView.as_view(), name="archived-user-create"),
    path("archival/users/<int:user_id>/restore/", views.RestoreArchivedUserView.as_view(), name="archived-user-restore"),
    path("archival/historical/", views.ArchivedHistoricalDataListView.as_view(), name="historical-data-list"),
    path("archival/historical/create/", views.ArchiveHistoricalDataView.as_view(), name="historical-data-create"),
    path("archival/historical/<int:data_id>/restore/", views.RestoreHistoricalDataView.as_view(), name="historical-data-restore"),
    path("purge-requests/", views.PurgeRequestListView.as_view(), name="purge-request-list"),
    path("purge-requests/create/", views.PurgeRequestCreateView.as_view(), name="purge-request-create"),
    path("purge-requests/<int:request_id>/authorize/", views.PurgeAuthorizeView.as_view(), name="purge-request-authorize"),

    # Audit Logs & Reports
    path("audit/", views.AuditLogListView.as_view(), name="audit-log-list"),
    path("audit/reports/", views.AuditReportView.as_view(), name="audit-report"),
    path("audit/sessions/", views.SessionListView.as_view(), name="session-log-list"),
    path("audit/alerts/", views.SecurityAlertListView.as_view(), name="security-alert-list"),
    path("notifications/", views.NotificationListView.as_view(), name="notification-list"),

    # Configuration
    path("config/", views.ConfigListView.as_view(), name="config-list"),
    path("config/<str:key>/", views.ConfigUpdateView.as_view(), name="config-update"),
]
