from rest_framework.permissions import BasePermission

MODULE_CODE = "leave"

PERM_APPLY = "leave.application.apply"
PERM_VIEW_SELF = "leave.application.view_self"
PERM_REVIEW = "leave.application.review"
PERM_ADMIN = "leave.admin.manage"


class HasPrincipal(BasePermission):
    def has_permission(self, request, view):
        return bool(request.principal and request.principal.user_id)


class CanApplyLeave(BasePermission):
    def has_permission(self, request, view):
        if not (request.principal and request.principal.user_id):
            return False
        return request.principal.has_permission(PERM_APPLY)


class CanViewLeave(BasePermission):
    def has_permission(self, request, view):
        if not (request.principal and request.principal.user_id):
            return False
        return (
            request.principal.has_permission(PERM_VIEW_SELF)
            or request.principal.has_permission(PERM_REVIEW)
            or request.principal.has_permission(PERM_ADMIN)
        )


class CanReviewLeave(BasePermission):
    def has_permission(self, request, view):
        if not (request.principal and request.principal.user_id):
            return False
        return (
            request.principal.has_permission(PERM_REVIEW)
            or request.principal.has_permission(PERM_ADMIN)
        )


class CanManageLeaveAdmin(BasePermission):
    def has_permission(self, request, view):
        if not (request.principal and request.principal.user_id):
            return False
        return request.principal.has_permission(PERM_ADMIN)
