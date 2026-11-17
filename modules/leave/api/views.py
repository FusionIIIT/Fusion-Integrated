from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest, LeaveLedger
from modules.leave.api.serializers import (
    LeaveTypeSerializer,
    LeaveBalanceSerializer,
    LeaveLedgerSerializer,
    LeaveRequestSerializer,
    LeaveRecommendationSerializer,
    LeaveApprovalSerializer,
)


class LeaveTypeListView(APIView):
    permission_classes = [HasModuleGrant("leave")]

    def get(self, request):
        types = LeaveType.objects.filter(is_active=True).order_by("code")
        return Response(LeaveTypeSerializer(types, many=True).data)


class MyLeaveBalancesView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.view")]

    def get(self, request):
        user_id = request.principal.user_id
        year = request.query_params.get("year", timezone.now().year)
        balances = LeaveBalance.objects.filter(user_id=user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class MyLeaveRequestsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.view_self")]

    def get(self, request):
        user_id = request.principal.user_id
        requests = LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(LeaveRequestSerializer(requests, many=True).data)

    def post(self, request):
        serializer = LeaveRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user_id = request.principal.user_id
        leave_type = serializer.validated_data["leave_type"]
        duration = serializer.validated_data["duration_days"]

        # Check balance
        current_year = timezone.now().year
        balance = LeaveBalance.objects.filter(
            user_id=user_id, leave_type=leave_type, year=current_year
        ).first()

        if balance and balance.remaining_days < float(duration):
            return Response(
                {"error": f"Insufficient leave balance for {leave_type.code}. Remaining: {balance.remaining_days} days."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave_req = serializer.save(user_id=user_id, status="PENDING_APPROVAL")
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


class CancelLeaveRequestView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.cancel")]

    def post(self, request, pk):
        user_id = request.principal.user_id
        leave_req = LeaveRequest.objects.filter(pk=pk, user_id=user_id).first()
        if not leave_req:
            return Response({"error": "Leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        if leave_req.status not in ["DRAFT", "PENDING_APPROVAL", "RECOMMENDED"]:
            return Response(
                {"error": f"Cannot cancel leave request in status '{leave_req.status}'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        leave_req.status = "CANCELLED"
        leave_req.save(update_fields=["status"])
        return Response(LeaveRequestSerializer(leave_req).data)


class LeaveLedgerListView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.balance.view")]

    def get(self, request):
        user_id = request.principal.user_id
        ledger_entries = LeaveLedger.objects.filter(user_id=user_id).order_by("-created_at")
        return Response(LeaveLedgerSerializer(ledger_entries, many=True).data)


class PendingApprovalsView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]

    def get(self, request):
        # Pending requests awaiting recommendation or sanction
        pending = LeaveRequest.objects.filter(status__in=["PENDING_APPROVAL", "RECOMMENDED"]).order_by("created_at")
        return Response(LeaveRequestSerializer(pending, many=True).data)


class RecommendLeaveRequestView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.recommend")]

    def post(self, request, pk):
        serializer = LeaveRecommendationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leave_req = LeaveRequest.objects.filter(pk=pk, status="PENDING_APPROVAL").first()
        if not leave_req:
            return Response({"error": "Pending leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        leave_req.status = "RECOMMENDED"
        leave_req.recommender_user_id = request.principal.user_id
        leave_req.recommendation_remarks = serializer.validated_data.get("remarks", "")
        leave_req.recommended_at = timezone.now()
        leave_req.save(update_fields=["status", "recommender_user_id", "recommendation_remarks", "recommended_at"])

        return Response(LeaveRequestSerializer(leave_req).data)


class LeaveApprovalView(APIView):
    permission_classes = [HasModuleGrant("leave"), HasPermission("leave.application.approve")]

    @transaction.atomic
    def post(self, request, pk):
        serializer = LeaveApprovalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        leave_req = LeaveRequest.objects.filter(pk=pk, status__in=["PENDING_APPROVAL", "RECOMMENDED"]).first()
        if not leave_req:
            return Response({"error": "Actionable leave request not found."}, status=status.HTTP_404_NOT_FOUND)

        action = serializer.validated_data["action"]
        remarks = serializer.validated_data.get("remarks", "")
        approver_id = request.principal.user_id

        if action == "approve":
            leave_req.status = "APPROVED"
            leave_req.approver_user_id = approver_id
            leave_req.approval_remarks = remarks
            leave_req.approved_at = timezone.now()
            leave_req.save(update_fields=["status", "approver_user_id", "approval_remarks", "approved_at"])

            # Deduct balance and record in LeaveLedger
            balance = LeaveBalance.objects.filter(
                user_id=leave_req.user_id,
                leave_type=leave_req.leave_type,
                year=leave_req.start_date.year,
            ).first()

            new_balance_days = Decimal("0.0")
            if balance:
                balance.used_days = balance.used_days + Decimal(str(leave_req.duration_days))
                balance.save(update_fields=["used_days"])
                new_balance_days = Decimal(str(balance.remaining_days))

            LeaveLedger.objects.create(
                user_id=leave_req.user_id,
                leave_type=leave_req.leave_type,
                transaction_type="DEBIT",
                days=leave_req.duration_days,
                balance_after=new_balance_days,
                reference_request=leave_req,
                remarks=f"Approved leave #{leave_req.pk}",
            )

        elif action == "reject":
            leave_req.status = "REJECTED"
            leave_req.approver_user_id = approver_id
            leave_req.rejection_reason = remarks
            leave_req.save(update_fields=["status", "approver_user_id", "rejection_reason"])

        return Response(LeaveRequestSerializer(leave_req).data)
