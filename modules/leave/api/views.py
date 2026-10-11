from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest
from modules.leave.api.serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveApprovalSerializer,
)


@extend_schema(responses=LeaveTypeSerializer(many=True))
class LeaveTypeListView(APIView):
    permission_classes = [HasModuleGrant("leave")]

    def get(self, request):
        types = LeaveType.objects.filter(is_active=True)
        return Response(LeaveTypeSerializer(types, many=True).data)


@extend_schema(responses=LeaveBalanceSerializer(many=True))
class MyLeaveBalancesView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.view")]

    def get(self, request):
        user_id = request.principal.user_id
        balances = LeaveBalance.objects.filter(user_id=user_id)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


@extend_schema(methods=["GET"], responses=LeaveRequestSerializer(many=True))
@extend_schema(
    methods=["POST"], request=LeaveRequestSerializer, responses=LeaveRequestSerializer
)
class MyLeaveRequestsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]

    def get_permissions(self):
        # POST creates an application, which the "Apply Leave" nav gates on
        # leave.application.create; listing remains view_self.
        if self.request.method == "POST":
            return [HasModuleGrant("leave"), HasPermission("leave.application.create")]
        return super().get_permissions()

    def get(self, request):
        user_id = request.principal.user_id
        requests = LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user_id = request.principal.user_id
        # Check leave balance
        leave_type = serializer.validated_data["leave_type"]
        duration = serializer.validated_data["duration_days"]
        
        balance = LeaveBalance.objects.filter(user_id=user_id, leave_type=leave_type).first()
        if balance and balance.remaining_days < float(duration):
            return Response(
                {"error": "Insufficient leave balance."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave_req = serializer.save(user_id=user_id, status="pending")
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=LeaveRequestSerializer)
class CancelLeaveRequestView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.cancel")]

    def post(self, request, pk):
        user_id = request.principal.user_id
        leave_req = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave_req:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)
        
        if leave_req.status != "pending":
            return Response(
                {"error": "Only pending leaves can be cancelled."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        leave_req.status = "cancelled"
        leave_req.save(update_fields=["status"])
        return Response(LeaveRequestSerializer(leave_req).data)


@extend_schema(responses=LeaveRequestSerializer(many=True))
class PendingApprovalsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]

    def get(self, request):
        # View pending leaves
        pending = LeaveRequest.objects.filter(status="pending").order_by("created_at")
        return Response(LeaveRequestSerializer(pending, many=True).data)


@extend_schema(request=LeaveApprovalSerializer, responses=LeaveRequestSerializer)
class LeaveApprovalView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]

    def post(self, request, pk):
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leave_req = LeaveRequest.objects.filter(pk=pk, status="pending").first()
        if not leave_req:
            return Response({"error": "Pending leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        action = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")
        approver_id = request.principal.user_id

        if action == "approve":
            leave_req.status = "approved"
            leave_req.approver_user_id = approver_id
            leave_req.approved_at = timezone.now()
            leave_req.save(update_fields=["status", "approver_user_id", "approved_at"])

            # Deduct balance
            balance = LeaveBalance.objects.filter(user_id=leave_req.user_id, leave_type=leave_req.leave_type).first()
            if balance:
                balance.used_days = float(balance.used_days) + float(leave_req.duration_days)
                balance.save(update_fields=["used_days"])

        elif action == "reject":
            leave_req.status = "rejected"
            leave_req.approver_user_id = approver_id
            leave_req.rejection_reason = remarks
            leave_req.save(update_fields=["status", "approver_user_id", "rejection_reason"])

        return Response(LeaveRequestSerializer(leave_req).data)
