"""Permission classes for Employee Leave Management (ELM).

Implements role-based authorization adhering to BR-EL-016..020, BR-EL-036, and CFR-EL-001.
Strict rule: Non-director applicants are strictly prohibited from approving their own leave (BR-EL-036).
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


def get_actor_id(request) -> int | None:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "user_id", None) is not None:
        return principal.user_id
    user = getattr(request, "user", None)
    if user and getattr(user, "user_id", None) is not None:
        return user.user_id
    if user and getattr(user, "id", None) is not None:
        return user.id
    return None


def get_actor_roles(request) -> set[str]:
    principal = getattr(request, "principal", None)
    if principal and getattr(principal, "roles", None) is not None:
        return set(principal.roles)
    user = getattr(request, "user", None)
    if user:
        if hasattr(user, "roles"):
            return set(user.roles)
        if getattr(user, "is_superuser", False) or getattr(user, "is_staff", False):
            return {"leave_admin"}
    return {"faculty", "staff"}


def has_actor_permission(request, perm_code: str) -> bool:
    principal = getattr(request, "principal", None)
    if principal and hasattr(principal, "has_permission"):
        return principal.has_permission(perm_code)
    roles = get_actor_roles(request)
    if "leave_admin" in roles:
        return True
    if perm_code == "elm.request.review" and bool(roles & {"unit_head", "hod"}):
        return True
    if perm_code == "elm.request.sanction" and bool(roles & {"dean", "registrar", "director"}):
        return True
    return False


class IsLeaveRequestOwner(BasePermission):
    """Applicant owns the leave request."""

    def has_object_permission(self, request, view, obj) -> bool:
        actor_id = get_actor_id(request)
        return obj.user_id == actor_id


class IsNominatedSubstitute(BasePermission):
    """Actor is the nominated substitute for the leave request."""

    def has_object_permission(self, request, view, obj) -> bool:
        actor_id = get_actor_id(request)
        return obj.substitute_id == actor_id


class CanReviewUnitHead(BasePermission):
    """Actor has authority to review as Unit Head. Prohibits self-review (BR-EL-036)."""

    def has_permission(self, request, view) -> bool:
        roles = get_actor_roles(request)
        return bool(roles & {"unit_head", "hod", "leave_admin"}) or has_actor_permission(
            request, "elm.request.review"
        )

    def has_object_permission(self, request, view, obj) -> bool:
        actor_id = get_actor_id(request)
        # Unit Head cannot review own leave (BR-EL-036)
        if obj.user_id == actor_id:
            return False
        return self.has_permission(request, view)


class CanSanctionLeave(BasePermission):
    """Actor has authority to make final sanction decisions (BR-EL-018, BR-EL-020, BR-EL-036)."""

    def has_permission(self, request, view) -> bool:
        roles = get_actor_roles(request)
        return bool(roles & {"dean", "director", "registrar", "leave_admin"}) or has_actor_permission(
            request, "elm.request.sanction"
        )

    def has_object_permission(self, request, view, obj) -> bool:
        actor_id = get_actor_id(request)
        roles = get_actor_roles(request)
        # Director self-sanction exception (BR-EL-020)
        if "director" in roles and obj.status == "awaiting_director_self_sanction":
            return obj.user_id == actor_id

        # All other applicants prohibited from self-sanction (BR-EL-036)
        if obj.user_id == actor_id:
            return False
        return self.has_permission(request, view)


class IsLeaveAdmin(BasePermission):
    """Actor is a Leave Administrator with calendar and maintenance privileges."""

    def has_permission(self, request, view) -> bool:
        roles = get_actor_roles(request)
        return "leave_admin" in roles or has_actor_permission(request, "elm.admin.manage")
