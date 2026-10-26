"""API permissions for Leave Management."""
from rest_framework.permissions import BasePermission

from fusion_auth.permissions import HasModuleGrant

HasModuleGrantLeave = HasModuleGrant("leave_management")


class DenyLeaveAction(BasePermission):
    """Fail closed when a viewset action has no declared permission."""

    def has_permission(self, request, view):
        return False


class LeaveActionPermissionMixin:
    """Apply the module grant and the permission declared for each action."""

    action_permissions = {}

    def get_permissions(self):
        required = self.action_permissions.get(self.action)
        if required is None:
            return [DenyLeaveAction()]
        return [permission() for permission in (HasModuleGrantLeave, *required)]


class IsLeaveRequestOwnerOrApprover(BasePermission):
    """Object-level permission for leave requests."""

    def has_object_permission(self, request, view, obj):
        principal = request.principal
        user_id = principal.user_id

        # Owner can view their own
        if obj.user_id == user_id:
            return True

        # Approvers can view if they have permission
        if principal.has_permission("leave_management.leave_request.view"):
            return True

        # Substitute can view substitute requests
        if principal.has_permission("leave_management.substitute_request.view_self") and hasattr(
            obj, "substitute_requests"
        ):
            return obj.substitute_requests.filter(substitute_id=user_id).exists()

        return False


class IsLeaveRequestOwner(BasePermission):
    """Restrict employee actions to the leave request owner."""

    def has_object_permission(self, request, view, obj):
        return obj.user_id == request.principal.user_id


class CanModifyPendingLeave(BasePermission):
    """Check if user can modify a pending leave request."""

    def has_object_permission(self, request, view, obj):
        principal = request.principal
        user_id = principal.user_id

        # Owner can modify if pending
        if obj.user_id == user_id and obj.status in ["draft", "submitted", "substitute_pending"]:
            return principal.has_permission("leave_management.leave_request.modify_pending")

        return False
