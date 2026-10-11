from rest_framework.permissions import BasePermission


class IsLeaveApplicant(BasePermission):
    """An employee can access their own leave applications."""

    def has_object_permission(self, request, view, obj):
        return obj.employee_id == request.user.id


class IsLeaveAdministrator(BasePermission):
    """Placeholder for the repository's authorized leave-admin role."""

    def has_permission(self, request, view):
        # Replace with the actual Fusion role/permission check.
        return (
            request.user.is_authenticated
            and request.user.has_perm("elm.manage_leave_records")
        )


class CanReviewLeave(BasePermission):
    """Placeholder for Unit Head/authority workflow permissions."""

    def has_permission(self, request, view):
        # Replace with the repository's configured reviewer roles,
        # assigned workflow tasks, and authority hierarchy checks.
        return (
            request.user.is_authenticated
            and request.user.has_perm("elm.review_leave")
        )
