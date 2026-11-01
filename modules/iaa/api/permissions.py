"""Fine-grained IAA role checks layered behind the IAM module-grant gate."""
from rest_framework.permissions import BasePermission

from modules.iaa.services.authz import active_role, role_has_permission


class HasIaaPermission(BasePermission):
    permission_code = ""
    message = "Your active IAA role cannot perform this action."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        role = active_role(request)
        return bool(principal and role and role_has_permission(
            principal, role, self.permission_code))


class HasAnyIaaPermission(BasePermission):
    permission_codes = ()
    message = "Your active IAA role cannot perform this action."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        role = active_role(request)
        return bool(principal and role and any(
            role_has_permission(principal, role, code)
            for code in self.permission_codes))


def IaaPermission(code: str):  # noqa: N802
    return type("IaaPermission_" + code.replace(".", "_"),
                (HasIaaPermission,), {"permission_code": code})


def IaaAnyPermission(*codes: str):  # noqa: N802
    return type("IaaAnyPermission_" + "_".join(c.replace(".", "_") for c in codes),
                (HasAnyIaaPermission,), {"permission_codes": codes})
