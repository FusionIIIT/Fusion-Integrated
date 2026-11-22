"""Permission classes for LMS endpoints."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class HasLmsPermission(BasePermission):
    code: str = ""

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        if not self.code:
            return True
        return principal.has_permission(self.code)


def RequireLmsPermission(code: str):  # noqa: N802
    return type(
        f"RequireLmsPermission_{code.replace('.', '_')}",
        (HasLmsPermission,),
        {"code": code},
    )
