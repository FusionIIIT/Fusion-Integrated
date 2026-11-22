"""DRF Permission classes for PSM endpoints."""

from rest_framework.permissions import BasePermission


class _PsmPermissionGate(BasePermission):
    codes: tuple[str, ...] = ()
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None) or getattr(request, "user", None)
        if principal is None or not getattr(principal, "is_authenticated", False):
            return False

        if not self.codes:
            return True

        if hasattr(principal, "has_any_permission"):
            return principal.has_any_permission(*self.codes)

        if hasattr(principal, "has_perm"):
            return any(principal.has_perm(c) for c in self.codes)

        return False


def RequirePermission(*codes: str):  # noqa: N802
    return type(
        "RequirePermission_" + "_".join(codes).replace(".", "_"),
        (_PsmPermissionGate,),
        {"codes": codes},
    )
