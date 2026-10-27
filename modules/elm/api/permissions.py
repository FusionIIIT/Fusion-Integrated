"""DRF Permission classes for ELM endpoints."""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class HasElmPermission(BasePermission):
    code: str = ""
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if not principal:
            return False
        return principal.has_permission(self.code)


def RequireElmPermission(perm_code: str):  # noqa: N802
    return type(
        f"RequireElmPermission_{perm_code.replace('.', '_')}",
        (HasElmPermission,),
        {"code": perm_code},
    )
