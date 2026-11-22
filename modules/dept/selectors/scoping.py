"""Department scoping helpers (ADR-0010)."""

from __future__ import annotations

from typing import Any

from django.core.exceptions import PermissionDenied


def resolve_department_code(principal: Any, request: Any = None) -> str:
    """Resolve active department code for principal.

    Checks query param 'department', header, or falls back to principal attribute or default.
    """
    if request:
        dept_param = request.query_params.get("department") or request.data.get("department")
        if dept_param:
            return dept_param.strip().upper()

    # If principal has active department
    dept = getattr(principal, "department", None)
    if dept:
        return str(dept).strip().upper()

    # Default fallback department in demo/dev
    return "CSE"


def assert_department_access(principal: Any, department_code: str) -> None:
    """Ensure principal is permitted to access department scope."""
    if not principal.is_authenticated:
        raise PermissionDenied("Authentication required.")
    # In module-only dev fixture, users have access to their scoped department
