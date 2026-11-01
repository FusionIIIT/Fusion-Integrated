from django.urls import path

from modules.superadmin.api.views import (
    CreateUserView,
    PasswordResetView,
    RoleDirectoryView,
    UserDirectoryView,
    UserImportView,
    UserRoleAssignmentView,
    UserRoleView,
)

urlpatterns = [
    path("users", UserDirectoryView.as_view(), name="superadmin-users"),
    path("users/create", CreateUserView.as_view(), name="superadmin-user-create"),
    path("users/import", UserImportView.as_view(), name="superadmin-user-import"),
    path("users/<str:username>/roles", UserRoleView.as_view(), name="superadmin-user-roles"),
    path(
        "users/<str:username>/roles/assign",
        UserRoleAssignmentView.as_view(),
        name="superadmin-user-role-assign",
    ),
    path(
        "users/<str:username>/password-reset",
        PasswordResetView.as_view(),
        name="superadmin-user-password-reset",
    ),
    path("roles", RoleDirectoryView.as_view(), name="superadmin-roles"),
]
