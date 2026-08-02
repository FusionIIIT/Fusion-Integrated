"""Permission classes for this module.

Institute users are authorised by permission codes; recruiters hold none, and
their authority is the company-scoped queryset instead. `ScopedCollection` is
the gate for an endpoint both may reach: it lets a recruiter through to the
selector and still demands a code from everyone else.
"""
from rest_framework.permissions import BasePermission


class _ScopedCollection(BasePermission):
    codes: tuple[str, ...] = ()
    message = "You do not have permission to view this."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        if getattr(principal, "kind", None) == "recruiter":
            return True        # authorised by scope, not by code
        return principal.has_any_permission(*self.codes)


def ScopedCollection(*codes: str):                          # noqa: N802
    return type("ScopedCollection_" + "_".join(codes).replace(".", "_"),
                (_ScopedCollection,), {"codes": codes})
