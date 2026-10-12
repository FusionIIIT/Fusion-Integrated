from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated

from fusion_auth.permissions import HasPermission
from modules.elm.api.serializers import (
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
)
from modules.elm.models import LeaveRequest


@extend_schema(responses=LeaveRequestSerializer(many=True))
class LeaveRequestListView(generics.ListAPIView):
    """List the authenticated employee's own leave applications."""

    serializer_class = LeaveRequestSerializer
    permission_classes = [
        IsAuthenticated,
        HasPermission("elm.application.view_self"),
    ]

    def get_queryset(self):
        return LeaveRequest.objects.filter(
            employee_id=self.request.principal.user_id
        ).order_by("-created_at")


class LeaveRequestCreateView(generics.CreateAPIView):
    """Submit a leave application for the authenticated employee."""

    serializer_class = LeaveRequestCreateSerializer
    permission_classes = [
        IsAuthenticated,
        HasPermission("elm.application.apply"),
    ]

    def perform_create(self, serializer):
        substitute_required = serializer.validated_data.get(
            "substitute_required", False
        )
        status = (
            LeaveRequest.Status.AWAITING_SUBSTITUTE
            if substitute_required
            else LeaveRequest.Status.UNIT_HEAD_REVIEW
        )
        serializer.save(
            employee_id=self.request.principal.user_id,
            status=status,
        )
