from rest_framework import generics
from rest_framework.exceptions import ValidationError

from fusion_auth.permissions import HasModuleGrant, HasPermission

from ..models import LeaveRequest, LeaveType
from .serializers import LeaveRequestSerializer, LeaveTypeSerializer
from rest_framework.response import Response


MODULE = HasModuleGrant("leave")


class LeaveTypeListView(generics.ListAPIView):
    queryset = LeaveType.objects.all().order_by("id")
    serializer_class = LeaveTypeSerializer
    permission_classes = [
        MODULE,
        HasPermission("leave.request.view_self"),
    ]


class LeaveRequestListView(generics.ListCreateAPIView):
    serializer_class = LeaveRequestSerializer

    def get_permissions(self):
        required = (
            "leave.request.create"
            if self.request.method == "POST"
            else "leave.request.view_self"
        )
        return [
            MODULE(),
            HasPermission(required)(),
        ]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class LeaveRequestDetailView(generics.RetrieveAPIView):
    serializer_class = LeaveRequestSerializer
    permission_classes = [
        MODULE,
        HasPermission("leave.request.view_self"),
    ]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user=self.request.user)


class LeaveRequestWithdrawView(generics.GenericAPIView):
    """Employees may withdraw their own request while it is still pending."""

    serializer_class = LeaveRequestSerializer
    permission_classes = [
        MODULE,
        HasPermission("leave.request.withdraw"),
    ]

    def get_queryset(self):
        return LeaveRequest.objects.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        leave_request = self.get_object()
        if leave_request.status != "pending":
            raise ValidationError(
                "Only pending leave requests can be withdrawn."
            )
        leave_request.status = "withdrawn"
        leave_request.save(update_fields=["status", "updated_at"])
        return Response(self.get_serializer(leave_request).data)
