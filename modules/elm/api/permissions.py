from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant

MODULE = HasModuleGrant("elm")


class HasElmPermission(BasePermission):
    code = ""

    def has_permission(self, request, view):
        actor = getattr(request, "principal", None)
        return bool(actor and actor.has_permission(self.code))


def permission(code):
    return type("HasPermission_" + code.replace(".", "_"), (HasElmPermission,), {"code": code})
