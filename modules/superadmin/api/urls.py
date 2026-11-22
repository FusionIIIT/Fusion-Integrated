"""URL routing for Super Admin."""
from django.urls import path

from modules.superadmin.api.views import (
    AuditEntryListAPIView,
    RoleAssignmentListCreateAPIView,
    RoleRevokeAPIView,
    UserAccountListCreateAPIView,
    UserArchiveAPIView,
    UserDeactivateAPIView,
    UserRestoreAPIView,
)

app_name = "superadmin"

urlpatterns = [
    path("users/", UserAccountListCreateAPIView.as_view(), name="user-list-create"),
    path(
        "users/<int:user_id>/deactivate/",
        UserDeactivateAPIView.as_view(),
        name="user-deactivate",
    ),
    path(
        "users/<int:user_id>/archive/",
        UserArchiveAPIView.as_view(),
        name="user-archive",
    ),
    path(
        "users/<int:user_id>/restore/",
        UserRestoreAPIView.as_view(),
        name="user-restore",
    ),
    path("roles/", RoleAssignmentListCreateAPIView.as_view(), name="role-list-create"),
    path("roles/<int:pk>/revoke/", RoleRevokeAPIView.as_view(), name="role-revoke"),
    path("audit/", AuditEntryListAPIView.as_view(), name="audit-list"),
]
