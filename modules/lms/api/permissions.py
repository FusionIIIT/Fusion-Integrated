"""Permission classes for LMS endpoints."""

from __future__ import annotations

from rest_framework.permissions import BasePermission


class HasLmsPermission(BasePermission):
    code: str = ""

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        if principal is None:
            return False
        if "lms" not in getattr(principal, "modules", ()):
            return False
        if not self.code:
            return True
        return principal.has_permission(self.code)


class RequireLmsPermission(HasLmsPermission):
    def __init__(self, code: str = ""):
        self.code = code

    def __call__(self):
        return self
