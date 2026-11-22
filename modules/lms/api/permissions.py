"""Permission classes for the LMS module."""
from rest_framework.permissions import BasePermission


class LmsPermission(BasePermission):
    """Checks module grant + a specific permission code."""
    code: str = ""
    module: str = "lms"

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        if not principal.has_module(self.module):
            return False
        if self.code:
            return principal.has_permission(self.code)
        return True


def LmsPerm(code: str):  # noqa: N802
    return type(f"LmsPerm_{code.replace('.', '_')}", (LmsPermission,), {"code": code})
