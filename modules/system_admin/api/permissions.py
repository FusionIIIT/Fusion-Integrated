"""API permissions for System Admin module.

Enforces Super Admin access boundaries and dual-authorization constraints
(CFR-SA-020, BR-SA-022, BR-SA-026).
"""
from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasPermission


class IsSuperAdminOperator(BasePermission):
    """Enforces that the caller is authenticated as a Super Admin operator."""

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if not principal or not principal.is_authenticated:
            return False
        # Either has system_admin module or has explicit operator kind
        return principal.has_module("system_admin") or principal.kind == "operator"


class IsITHeadAuthorizer(BasePermission):
    """Enforces that the caller is the IT Head for dual purge authorization (BR-SA-022)."""

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if not principal or not principal.is_authenticated:
            return False
        return principal.has_permission("system_admin.purge.authorize")
