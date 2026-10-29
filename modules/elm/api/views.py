from rest_framework import generics

from fusion_auth.permissions import HasPermission
from modules.elm.api.serializers import (
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
)
from modules.elm.models import LeaveApplication


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    def get_queryset(self):
        return LeaveApplication.objects.filter(
            user_id=self.request.principal.user_id,
        )

    def get_serializer_class(self):
        if self.request.method == "POST":
            return LeaveApplicationCreateSerializer
        return LeaveApplicationSerializer

    def get_permissions(self):
        permission = (
            "elm.leave_application.apply"
            if self.request.method == "POST"
            else "elm.leave_application.view_self"
        )
        return [HasPermission(permission)()]

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.principal.user_id)