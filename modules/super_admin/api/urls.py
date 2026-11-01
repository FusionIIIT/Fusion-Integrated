from django.urls import path
from modules.super_admin.api.views import (
    UserManagementView,
    UserStatusView,
    RoleAssignmentView,
    RoleRevokeView,
    AuditLogListView,
)

urlpatterns = [
    path("users", UserManagementView.as_view(), name="sa-users"),
    path("users/<int:pk>/status", UserStatusView.as_view(), name="sa-user-status"),
    path("roles/assign", RoleAssignmentView.as_view(), name="sa-role-assign"),
    path("roles/<int:pk>/revoke", RoleRevokeView.as_view(), name="sa-role-revoke"),
    path("audit-logs", AuditLogListView.as_view(), name="sa-audit-logs"),
]
