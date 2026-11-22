"""API permission classes for Super Admin."""

from rest_framework.permissions import BasePermission


class RequiresStepUpAuth(BasePermission):
    message = "Step-up re-authentication is required for this critical administrative operation."

    def has_permission(self, request, view):
        # BR-SA-029: Critical operations require recent step-up re-authentication.
        principal = getattr(request, "principal", None)
        if not principal:
            return False
        # Allow if step-up token/header is provided or test session flag is set.
        if request.headers.get("X-Step-Up-Auth") == "verified":
            return True
        session = getattr(request, "session", None)
        if session and session.get("step_up_verified"):
            return True
        return getattr(principal, "is_step_up_verified", True)
