from rest_framework import generics

from fusion_auth.permissions import (
    HasModuleGrant,
    HasPermission,
    IsAuthenticatedPrincipal,
)
from modules.leave_elm.api.serializers import LeaveApplicationSerializer
from modules.leave_elm.models import LeaveApplication


MODULE = HasModuleGrant("leave_elm")
VIEW_PERMISSION = HasPermission("leave_elm.application.view")
APPLY_PERMISSION = HasPermission("leave_elm.application.apply")


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = LeaveApplicationSerializer
    permission_classes = [IsAuthenticatedPrincipal, MODULE]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if principal is None:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(employee_id=principal.user_id)

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                IsAuthenticatedPrincipal(),
                MODULE(),
                APPLY_PERMISSION(),
            ]
        return [
            IsAuthenticatedPrincipal(),
            MODULE(),
            VIEW_PERMISSION(),
        ]

    def perform_create(self, serializer):
        serializer.save(employee_id=self.request.principal.user_id)


class LeaveApplicationDetailView(generics.RetrieveAPIView):
    serializer_class = LeaveApplicationSerializer
    permission_classes = [
        IsAuthenticatedPrincipal,
        MODULE,
        VIEW_PERMISSION,
    ]

    def get_queryset(self):
        principal = getattr(self.request, "principal", None)
        if principal is None:
            return LeaveApplication.objects.none()
        return LeaveApplication.objects.filter(employee_id=principal.user_id)
