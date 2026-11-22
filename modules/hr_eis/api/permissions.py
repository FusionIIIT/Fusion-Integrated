from rest_framework import permissions

class HasModulePermission(permissions.BasePermission):
    """Enforces Fusion RBAC module permissions for EIS (BR-HR-002, BR-HR-030)."""
    required_perm = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # In test mode or admin bypass
        if getattr(request.user, "is_superuser", False) or getattr(request.user, "is_staff", False):
            return True
        user_perms = getattr(request, "module_permissions", [])
        perm = getattr(view, "required_permission", self.required_perm)
        if not perm:
            return True
        return perm in user_perms
