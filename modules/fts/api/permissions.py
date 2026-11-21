"""FTS permission classes (BR-FTS-001, AFR-FTS-009)."""
from rest_framework.permissions import BasePermission


class IsInstituteEmployee(BasePermission):
    """Enforce that only institute employees (faculty/staff) perform operational actions."""

    message = "Only institute employees (faculty/staff) may perform operational file actions."

    def has_permission(self, request, view):
        principal = getattr(request, "principal", None)
        if not principal:
            return False
        if getattr(principal, "kind", None) == "admin":
            return False
        if getattr(principal, "active_role", None) in ("admin", "system_admin"):
            return False
        if getattr(principal, "kind", None) in ("faculty", "staff"):
            return True
        return any(r in ("faculty", "staff") for r in getattr(principal, "roles", ()))
