"""Permission classes for the Employee Leave Management module.

Institute users are authorised by permission codes; the selector narrows the
queryset so a row outside scope is absent (404) rather than forbidden (403).
"""

from rest_framework.permissions import BasePermission


class _ScopedCollection(BasePermission):
    codes: tuple[str, ...] = ()

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        if getattr(principal, "kind", None) == "recruiter":
            return True  # authorised by scope, not by a grant
        return principal.has_any_permission(*self.codes)


def ScopedCollection(*codes: str):
    return type(
        "ScopedCollection_" + "_".join(codes).replace(".", "_"),
        (_ScopedCollection,),
        {"codes": codes},
    )
