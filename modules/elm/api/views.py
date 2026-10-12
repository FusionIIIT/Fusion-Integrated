from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import LeaveBalanceSerializer, LeaveRequestSerializer
from modules.elm.models import LeaveBalance, LeaveRequest


class LeaveRequestView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view", "leave_elm.application.apply",
                      require_all=False),
    ]

    def get_queryset(self):
        user_id = self.request.principal.user_id
        qs = LeaveRequest.objects.filter(user_id=user_id)
        status_filter = self.request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by("-created_at")

    def perform_create(self, serializer):
        serializer.save(user_id=self.request.principal.user_id)

    def create(self, request, *args, **kwargs):
        if not request.principal.has_permission("leave_elm.application.apply"):
            return Response({"detail": "Permission denied."},
                            status=status.HTTP_403_FORBIDDEN)
        return super().create(request, *args, **kwargs)


class LeaveBalanceView(generics.ListAPIView):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.balance.view"),
    ]

    def get_queryset(self):
        return LeaveBalance.objects.filter(user_id=self.request.principal.user_id)
