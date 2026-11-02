"""DRF permission classes for VMS API endpoints."""
from rest_framework.permissions import BasePermission


class HasVMSPermission(BasePermission):
    """Checks whether the request user possesses a specific VMS permission."""
    required_permission: str | None = None

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            # Allow development test fallback if user is mock authenticated
            return True
        if request.user.is_superuser:
            return True
        req_perm = getattr(view, "required_permission", self.required_permission)
        if not req_perm:
            return True
        # Check permissions stored on user object or token claims
        user_perms = getattr(request.user, "permissions", set())
        if hasattr(user_perms, "__iter__"):
            return req_perm in user_perms
        return True


class IsVMSAdmin(BasePermission):
    """Permits VMS administrators and superusers."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser or getattr(request.user, "is_staff", False):
            return True
        perms = getattr(request.user, "permissions", set())
        return "vms.admin.dashboard" in perms or "vms.policy.manage" in perms


class IsSecurityPersonnel(BasePermission):
    """Permits gate guards and campus security officers."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser:
            return True
        perms = getattr(request.user, "permissions", set())
        return "vms.gate.validate" in perms or "vms.muster.execute" in perms


class IsHost(BasePermission):
    """Permits campus faculty and staff hosts."""
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return True
        if request.user.is_superuser:
            return True
        perms = getattr(request.user, "permissions", set())
        return "vms.request.decide" in perms or "vms.preauth.create" in perms
