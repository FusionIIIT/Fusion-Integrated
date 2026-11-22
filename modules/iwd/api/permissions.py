from rest_framework import permissions


class HasRolePermission(permissions.BasePermission):
    """
    Checks role against HTTP header 'X-Role' or request.user.role.
    Strictly enforces distinct Department Head (hod) and Dean (dean).
    """
    def has_permission(self, request, view):
        role = request.headers.get("X-Role") or getattr(request.user, "role", None)
        allowed_roles = getattr(view, "allowed_roles", None)
        if not allowed_roles:
            return True
        return role in allowed_roles
