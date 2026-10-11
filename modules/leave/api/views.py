from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
)
from modules.leave.models import LeaveRequest


class LeaveRequestView(APIView):
    """Minimal employee leave API: list and submit own leave requests."""

    def get_permissions(self):
        if self.request.method == "POST":
            return [
                HasModuleGrant("leave"),
                HasPermission("leave.leave_request.create"),
            ]
        return [
            HasModuleGrant("leave"),
            HasPermission("leave.leave_request.view_self", "leave.leave_request.view_all"),
        ]

    def get(self, request, *args, **kwargs):
        if request.principal.has_permission("leave.leave_request.view_all"):
            queryset = LeaveRequest.objects.all()
        else:
            queryset = LeaveRequest.objects.filter(employee_id=request.principal.user_id)
        serializer = LeaveRequestSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request, *args, **kwargs):
        serializer = LeaveRequestCreateSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        leave_request = serializer.save()
        return Response(
            LeaveRequestSerializer(leave_request).data,
            status=201,
        )
