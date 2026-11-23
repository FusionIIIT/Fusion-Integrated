"""The second gate: a permission held through the role this person is acting as."""

from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant
from modules.gymkhana.selectors.access import may

MODULE = HasModuleGrant("gymkhana")


class _Acting(BasePermission):
    codes: tuple[str, ...] = ()
    message = "You do not have permission to perform this action in your current role."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        return principal is not None and any(may(principal, code) for code in self.codes)


def Acting(*codes: str):  # noqa: N802
    return type("Acting_" + "_".join(codes).replace(".", "_"), (_Acting,), {"codes": codes})
