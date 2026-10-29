from rest_framework import viewsets
from rest_framework.exceptions import PermissionDenied

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.models import Leave
from .serializers import LeaveSerializer


MODULE = HasModuleGrant("elm")

P_VIEW_SELF = "elm.leave.view_self"
P_CREATE = "elm.leave.create"
P_VIEW = "elm.leave.view"
P_MANAGE = "elm.leave.manage"


class LeaveViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveSerializer

    def get_permissions(self):
        if self.action == "list":
            return [MODULE(), HasPermission(P_VIEW_SELF, P_VIEW)()]
        if self.action == "retrieve":
            return [MODULE(), HasPermission(P_VIEW_SELF, P_VIEW)()]
        if self.action == "create":
            return [MODULE(), HasPermission(P_CREATE)()]
        if self.action in ("update", "partial_update", "destroy"):
            return [MODULE(), HasPermission(P_MANAGE)()]

        return [MODULE(), HasPermission(P_VIEW_SELF, P_VIEW)()]

    def get_queryset(self):
        principal = self.request.principal

        queryset = Leave.objects.select_related("employee")

        if principal.has_permission(P_VIEW) or principal.has_permission(P_MANAGE):
            return queryset

        return queryset.filter(employee__user_id=principal.user_id)

    def perform_create(self, serializer):
        principal = self.request.principal

        if not principal.has_permission(P_CREATE):
            raise PermissionDenied("You cannot create leave requests.")

        serializer.save(
            employee_id=principal.user_id,
            status="submitted",
        )