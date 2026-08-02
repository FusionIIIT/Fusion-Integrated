"""Two gates on every request, both server-side.

    HasModuleGrant   is this module yours at all?   (coarse — drives the sidebar)
    HasPermission    may you do this action?        (fine)

Both must pass. The default is deny: a view that declares nothing gets
IsAuthenticatedPrincipal and nothing more, so forgetting to think about
authorization fails closed rather than open.
"""
from rest_framework.permissions import BasePermission


class IsAuthenticatedPrincipal(BasePermission):
    message = "Authentication required."

    def has_permission(self, request, view):
        return getattr(request, "principal", None) is not None


class _HasModuleGrant(BasePermission):
    module_code = ""
    message = "This module is not available to your role."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        return p is not None and p.has_module(self.module_code)


def HasModuleGrant(module_code: str):                       # noqa: N802
    return type("HasModuleGrant_" + module_code,
                (_HasModuleGrant,), {"module_code": module_code})


class _HasPermission(BasePermission):
    codes: tuple[str, ...] = ()
    require_all = False
    message = "You do not have permission to perform this action."

    def has_permission(self, request, view):
        p = getattr(request, "principal", None)
        if p is None:
            return False
        if self.require_all:
            return all(p.has_permission(c) for c in self.codes)
        return p.has_any_permission(*self.codes)


def HasPermission(*codes: str, require_all: bool = False):  # noqa: N802
    return type("HasPermission_" + "_".join(codes).replace(".", "_"),
                (_HasPermission,), {"codes": codes, "require_all": require_all})
