"""Permission classes for SPACS API."""

from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant, HasPermission


def RequirePermission(*codes: str):  # noqa: N802
    """Helper requiring spacs module grant and at least one permission code."""
    grant_factory = HasModuleGrant("spacs")
    perm_factory = HasPermission(*codes)

    class _CombinedPermission(BasePermission):
        message = "You do not have permission to perform this action in SPACS."

        def has_permission(self, request, view):
            if not grant_factory().has_permission(request, view):
                return False
            return perm_factory().has_permission(request, view)

    return _CombinedPermission
