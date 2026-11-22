from rest_framework import permissions


class HasIwdPermission(permissions.BasePermission):
    """Enforces active-role permission checks for IWD endpoints."""

    def __init__(self, required_permission: str):
        self.required_permission = required_permission

    def __call__(self):
        return self

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        # In module-only / session-auth, check request.session or active_role grants
        user_permissions = getattr(request, "user_permissions", None)
        if user_permissions and self.required_permission in user_permissions:
            return True

        role = getattr(request, "active_role", None) or request.headers.get("X-Active-Role", "employee")
        from modules.iwd.registry import ROLE_GRANTS
        grants = ROLE_GRANTS.get(role, [])
        return self.required_permission in grants
