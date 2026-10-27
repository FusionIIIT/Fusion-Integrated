from django.db import transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response

from core.api.pagination import CursorPagination
from fusion_auth.permissions import HasModuleGrant, HasPermission

from .models import LeaveType, LeaveBalance, LeaveRequest
from .serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveApprovalSerializer,
)

MODULE = HasModuleGrant("elm")


class LeaveTypeViewSet(viewsets.ModelViewSet):
    queryset = LeaveType.objects.all()
    serializer_class = LeaveTypeSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [MODULE(), HasPermission("elm.leave_request.view")()]
        # TODO: separate leave_type.manage permission
        return [MODULE(), HasPermission("elm.leave_request.review")()]


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LeaveBalanceSerializer
    permission_classes = [MODULE, HasPermission("elm.leave_request.view")]

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        if not p:
            return LeaveBalance.objects.none()
        if p.has_permission("elm.leave_request.review"):
            return LeaveBalance.objects.select_related("leave_type").all()
        return LeaveBalance.objects.filter(user_id=p.user_id).select_related("leave_type")


class LeaveRequestViewSet(viewsets.ModelViewSet):
    serializer_class = LeaveRequestSerializer
    pagination_class = CursorPagination

    def get_permissions(self):
        if self.action == "create":
            return [MODULE(), HasPermission("elm.leave_request.create")()]
        if self.action in ["approve_reject", "pending"]:
            return [MODULE(), HasPermission("elm.leave_request.review")()]
        return [MODULE(), HasPermission("elm.leave_request.view")()]

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        if not p:
            return LeaveRequest.objects.none()
        qs = LeaveRequest.objects.select_related("leave_type")
        if p.has_permission("elm.leave_request.review"):
            return qs.all()
        return qs.filter(employee_user_id=p.user_id)

    def perform_create(self, serializer):
        p = getattr(self.request, "principal", None)
        user_id = p.user_id if p else None
        serializer.save(employee_user_id=user_id)

    @action(detail=True, methods=["post"], permission_classes=[MODULE, HasPermission("elm.leave_request.review")])
    def approve_reject(self, request, pk=None):
        leave = self.get_object()
        p = getattr(request, "principal", None)
        user_id = p.user_id if p else None

        if leave.employee_user_id == user_id:
            return Response(
                {"detail": "You cannot approve or reject your own leave request."},
                status=status.HTTP_403_FORBIDDEN,
            )

        if leave.status != "pending":
            return Response(
                {"detail": "Only pending requests can be reviewed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = LeaveApprovalSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        action_val = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")

        with transaction.atomic():
            if action_val == "approve":
                days = (leave.end_date - leave.start_date).days + 1
                try:
                    balance = LeaveBalance.objects.get(
                        user_id=leave.employee_user_id,
                        leave_type=leave.leave_type,
                        year=leave.start_date.year,
                    )
                except LeaveBalance.DoesNotExist:
                    return Response(
                        {"detail": "Leave balance record does not exist for this year."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                balance.used_days += days
                balance.save()
                leave.status = "approved"
            else:
                leave.status = "rejected"

            leave.reviewed_by_user_id = user_id
            leave.reviewed_at = timezone.now()
            leave.remarks = remarks
            leave.save()

        return Response({"status": leave.status}, status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"], permission_classes=[MODULE, HasPermission("elm.leave_request.review")])
    def pending(self, request):
        qs = LeaveRequest.objects.filter(status="pending").select_related("leave_type")
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)
