"""Quiz-specific HTTP permission checks."""

from rest_framework.permissions import BasePermission


class IsStudentPrincipal(BasePermission):
    """Require the IAM basic student identity for Student-only endpoints."""

    message = "This operation is available to Student principals only."

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        return principal is not None and getattr(principal, "kind", None) == "student"


class IsNotStudentPrincipal(BasePermission):
    """Keep Professor-oriented actions away from Student basic-role sessions."""

    message = "This operation is not available to Student principals."

    def has_permission(self, request, view) -> bool:
        principal = getattr(request, "principal", None)
        return principal is not None and getattr(principal, "kind", None) != "student"
