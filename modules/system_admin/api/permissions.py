"""DRF custom permission classes for modules.system_admin.

Gating endpoints using Principal resolved by IAM via fusion_auth.
Traceability: BR-SA-022, BR-SA-026, BR-SA-028, BR-SA-029.
"""
from __future__ import annotations

import logging
from typing import Any

from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import BasePermission

from modules.system_admin.services import security as security_service

logger = logging.getLogger(__name__)

SUPER_ADMIN_ROLES = {"super_admin", "system_admin"}
SUPER_ADMIN_PERMISSIONS = {
    "admin:access",
    "system_admin.access",
    "system_admin:access",
    "system_admin:full_control",
}

IT_HEAD_ROLES = {"it_head", "head_it", "director"}
IT_HEAD_PERMISSIONS = {
    "it_head:access",
    "system_admin:purge_authorize",
}

FORBIDDEN_OPERATIONAL_PATTERNS = {
    "grades",
    "transcripts",
    "payroll",
    "fee_ledger",
    "medical_records",
    "grievance_details",
    "complaint_records",
}


def _get_principal(request: Any) -> Any:
    return getattr(request, "principal", None) or getattr(request, "user", None)


def _extract_user_id(obj: Any) -> int | None:
    if obj is None:
        return None
    for attr in ("basic_user_id", "id", "user_id"):
        val = getattr(obj, attr, None)
        if isinstance(val, int):
            return val
    for attr in ("basic_user_id", "id", "user_id"):
        val = getattr(obj, attr, None)
        if isinstance(val, str):
            try:
                return int(val)
            except (ValueError, TypeError):
                continue
    return None


class IsSuperAdminPrincipal(BasePermission):
    """Gates access to Super Admin administrative plane (CFR-SA-001..023)."""

    message = "Super Admin privileges required."

    def has_permission(self, request: Any, view: Any) -> bool:
        principal = _get_principal(request)
        if principal is None:
            return False

        if getattr(principal, "is_super_admin", False) is True:
            return True

        if getattr(principal, "kind", None) in SUPER_ADMIN_ROLES:
            return True

        active_role = getattr(principal, "active_role", None)
        if active_role in SUPER_ADMIN_ROLES:
            return True

        user_roles = set(getattr(principal, "roles", ()))
        if user_roles & SUPER_ADMIN_ROLES:
            return True

        if hasattr(principal, "has_any_permission") and principal.has_any_permission(*SUPER_ADMIN_PERMISSIONS):
            return True

        permissions = getattr(principal, "permissions", set())
        if permissions & SUPER_ADMIN_PERMISSIONS:
            return True

        return False


class IsITHeadPrincipal(BasePermission):
    """Gates access to permanent purge authorization endpoint (BR-SA-022, CW-SA-01).

    Enforces dual-role segregation between Super Admin and IT Head.
    """

    message = "IT Head privileges required for permanent purge authorization (BR-SA-022)."

    def has_permission(self, request: Any, view: Any) -> bool:
        principal = _get_principal(request)
        if principal is None:
            return False

        active_role = getattr(principal, "active_role", None)
        if active_role in IT_HEAD_ROLES:
            return True

        user_roles = set(getattr(principal, "roles", ()))
        if user_roles & IT_HEAD_ROLES:
            return True

        if hasattr(principal, "has_any_permission") and principal.has_any_permission(*IT_HEAD_PERMISSIONS):
            return True

        permissions = getattr(principal, "permissions", set())
        if permissions & IT_HEAD_PERMISSIONS:
            return True

        return False


class DenySelfModification(BasePermission):
    """Forbids a Super Admin from changing their own privileges or account status (BR-SA-028)."""

    message = "Super Admin cannot self-modify their own account or status (BR-SA-028)."

    def has_permission(self, request: Any, view: Any) -> bool:
        principal = _get_principal(request)
        if principal is None:
            return True

        principal_id = _extract_user_id(principal)
        if principal_id is None:
            return True

        lookup_id = None
        if hasattr(view, "kwargs") and view.kwargs:
            lookup_id = view.kwargs.get("pk") or view.kwargs.get("user_id")
        if lookup_id is not None:
            try:
                if int(lookup_id) == principal_id:
                    raise PermissionDenied(self.message)
            except (ValueError, TypeError):
                pass

        return True

    def has_object_permission(self, request: Any, view: Any, obj: Any) -> bool:
        principal = _get_principal(request)
        if principal is None:
            return True

        principal_id = _extract_user_id(principal)
        target_user_id = _extract_user_id(obj)

        if principal_id is not None and target_user_id is not None and principal_id == target_user_id:
            raise PermissionDenied(self.message)

        return True


class RequiresCriticalActionConfirmation(BasePermission):
    """Enforces fresh credential confirmation for destructive operations (BR-SA-029)."""

    message = "Critical action requires valid re-authentication credentials (BR-SA-029)."

    def has_permission(self, request: Any, view: Any) -> bool:
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True

        principal = _get_principal(request)
        if principal is None:
            return False

        admin_user_id = _extract_user_id(principal)

        # Check headers first
        confirm_password = request.headers.get("X-Confirm-Password") if hasattr(request, "headers") else request.META.get("HTTP_X_CONFIRM_PASSWORD")
        confirm_totp = request.headers.get("X-Confirm-2FA", "") if hasattr(request, "headers") else request.META.get("HTTP_X_CONFIRM_2FA", "")

        # Fallback to request payload for POST/PATCH
        if not confirm_password and hasattr(request, "data") and isinstance(request.data, dict):
            confirm_password = request.data.get("confirm_password")
            confirm_totp = request.data.get("confirm_totp", "")

        if not confirm_password:
            raise PermissionDenied("Missing required re-authentication header X-Confirm-Password (BR-SA-029).")

        if admin_user_id:
            is_valid = security_service.verify_critical_action_reauth(
                admin_user_id=int(admin_user_id),
                password=str(confirm_password),
                totp_code=str(confirm_totp),
            )
            if not is_valid:
                raise PermissionDenied("Re-authentication failed: Invalid credentials (BR-SA-029).")

        return True


class EnforceDataIsolationBoundary(BasePermission):
    """Asserts that requests do not attempt to read or mutate operational module data (BR-SA-026)."""

    message = "Access to operational data is forbidden under Super Admin boundary (BR-SA-026)."

    def has_permission(self, request: Any, view: Any) -> bool:
        path = request.path.lower()
        for forbidden in FORBIDDEN_OPERATIONAL_PATTERNS:
            if forbidden in path:
                raise PermissionDenied(f"Operational domain data access '{forbidden}' is prohibited (BR-SA-026).")

        query_dict = getattr(request, "query_params", getattr(request, "GET", {}))
        query_keys = set(k.lower() for k in query_dict.keys())
        for forbidden in FORBIDDEN_OPERATIONAL_PATTERNS:
            if forbidden in query_keys:
                raise PermissionDenied(f"Operational domain query parameter '{forbidden}' is prohibited (BR-SA-026).")

        return True
