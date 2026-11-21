from __future__ import annotations

from datetime import date
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    ApplyLeaveInputSerializer,
    SubstituteActionInputSerializer,
    ReviewActionInputSerializer,
)
from modules.elm.domain.rules import ENTITLEMENTS
from modules.elm.models import LeaveBalance, LeaveRequest, SubstituteAssignment
from modules.elm.services.leave import (
    apply_for_leave,
    respond_substitute,
    review_leave_request,
    withdraw_leave_request,
    cancel_approved_leave,
    extend_leave,
    execute_year_end_processing,
    submit_resumption_of_duty,
    review_resumption,
    record_offline_sanctioned_leave,
)


class LeaveCatalogView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        return Response({
            "entitlements": {key: str(value) for key, value in ENTITLEMENTS.items()}
        })


class MyLeaveBalancesView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        user_id = request.principal.user_id
        current_year = timezone.now().year
        balances = LeaveBalance.objects.filter(user_id=user_id, year=current_year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class MyLeaveRequestsView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        user_id = request.principal.user_id
        requests = LeaveRequest.objects.filter(user_id=user_id).order_by("-created_at")
        serializer = LeaveRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        serializer = ApplyLeaveInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        leave_req = apply_for_leave(
            user_id=request.principal.user_id,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            half_day=data.get("half_day"),
            purpose=data["purpose"],
            is_station_leave=data.get("is_station_leave", False),
            destination=data.get("destination", ""),
            emergency_contact=data.get("emergency_contact", ""),
            substitute_id=data.get("substitute_id"),
        )
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


class LeaveRequestDetailView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request, pk: int):
        leave_req = LeaveRequest.objects.filter(id=pk, user_id=request.principal.user_id).first()
        if not leave_req:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        return Response(LeaveRequestSerializer(leave_req).data)


class WithdrawLeaveView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        leave_req = withdraw_leave_request(user_id=request.principal.user_id, request_id=pk)
        return Response(LeaveRequestSerializer(leave_req).data)


class CancelLeaveView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        today = timezone.now().date()
        leave_req = cancel_approved_leave(user_id=request.principal.user_id, request_id=pk, today_date=today)
        return Response(LeaveRequestSerializer(leave_req).data)


class SubstituteTasksView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request):
        user_id = request.principal.user_id
        pending_assignments = SubstituteAssignment.objects.filter(
            substitute_id=user_id, status="pending"
        ).select_related("leave_request")
        requests = [a.leave_request for a in pending_assignments]
        return Response(LeaveRequestSerializer(requests, many=True).data)


class RespondSubstituteView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def post(self, request, pk: int):
        serializer = SubstituteActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        assignment = respond_substitute(
            substitute_id=request.principal.user_id,
            request_id=pk,
            action=serializer.validated_data["action"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response({"status": assignment.status})


class ReviewTasksView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.review")]

    def get(self, request):
        pending_requests = LeaveRequest.objects.filter(
            status__in=["under_review", "recommended"]
        ).order_by("-created_at")
        return Response(LeaveRequestSerializer(pending_requests, many=True).data)


class ReviewDecisionView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.review")]

    def post(self, request, pk: int):
        serializer = ReviewActionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        leave_req = review_leave_request(
            reviewer_id=request.principal.user_id,
            request_id=pk,
            action=serializer.validated_data["action"],
            reason=serializer.validated_data.get("reason", ""),
        )
        return Response(LeaveRequestSerializer(leave_req).data)


class ExtendLeaveView(APIView):
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        new_end_date_str = request.data.get("new_end_date")
        if not new_end_date_str:
            return Response({"detail": "new_end_date is required"}, status=status.HTTP_400_BAD_REQUEST)
        new_end_date = date.fromisoformat(new_end_date_str)
        reason = request.data.get("reason", "")
        leave_req = extend_leave(
            user_id=request.principal.user_id,
            request_id=pk,
            new_end_date=new_end_date,
            reason=reason,
        )
        return Response(LeaveRequestSerializer(leave_req).data)


class PrintableLeaveView(APIView):
    """CFR-EL-023: Exportable/printable leave application data."""
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.view_self")]

    def get(self, request, pk: int):
        leave_req = LeaveRequest.objects.filter(id=pk, user_id=request.principal.user_id).first()
        if not leave_req:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
        history = list(leave_req.actions.values("actor_id", "action", "comments", "created_at"))
        return Response({
            "application_id": leave_req.id,
            "applicant_id": leave_req.user_id,
            "category": leave_req.category,
            "period": f"{leave_req.start_date} to {leave_req.end_date}",
            "leave_days": str(leave_req.leave_days),
            "status": leave_req.status,
            "purpose": leave_req.purpose,
            "station_leave": {
                "required": leave_req.is_station_leave,
                "destination": leave_req.destination,
                "emergency_contact": leave_req.emergency_contact,
            },
            "substitute_id": leave_req.substitute_id,
            "audit_trail": history,
            "generated_at": timezone.now().isoformat(),
        })


class YearEndProcessingView(APIView):
    """CFR-EL-028: Administrative Year-end leave processing."""
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.policy.manage")]

    def post(self, request):
        target_user_id = request.data.get("user_id", request.principal.user_id)
        year = int(request.data.get("year", timezone.now().year))
        res = execute_year_end_processing(user_id=int(target_user_id), year=year)
        return Response({key: str(val) for key, val in res.items()})


class SubmitResumptionView(APIView):
    """CFR-EL-021 & EL-UC-010: Submit Resumption of Duty."""
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.apply")]

    def post(self, request, pk: int):
        date_str = request.data.get("resumption_date")
        if not date_str:
            return Response({"detail": "resumption_date is required"}, status=status.HTTP_400_BAD_REQUEST)
        resumption_date = date.fromisoformat(date_str)
        details = request.data.get("details", "")
        leave_req = submit_resumption_of_duty(
            user_id=request.principal.user_id,
            request_id=pk,
            actual_resumption_date=resumption_date,
            details=details,
        )
        return Response(LeaveRequestSerializer(leave_req).data)


class ReviewResumptionView(APIView):
    """CFR-EL-021 & EL-UC-011: Review Resumption and adjust days."""
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.leave.review")]

    def post(self, request, pk: int):
        remarks = request.data.get("remarks", "")
        leave_req = review_resumption(
            reviewer_id=request.principal.user_id,
            request_id=pk,
            review_remarks=remarks,
        )
        return Response(LeaveRequestSerializer(leave_req).data)


class RecordOfflineLeaveView(APIView):
    """CFR-EL-027 & EL-UC-016: Record already sanctioned offline leave."""
    permission_classes = [HasModuleGrant("elm"), HasPermission("elm.policy.manage")]

    def post(self, request):
        user_id = int(request.data["user_id"])
        category = request.data["category"]
        start_date = date.fromisoformat(request.data["start_date"])
        end_date = date.fromisoformat(request.data["end_date"])
        purpose = request.data.get("purpose", "Offline approved leave")
        sanction_ref = request.data.get("sanction_reference", "OFFLINE-RECORD")

        leave_req = record_offline_sanctioned_leave(
            admin_id=request.principal.user_id,
            user_id=user_id,
            category=category,
            start_date=start_date,
            end_date=end_date,
            purpose=purpose,
            sanction_reference=sanction_ref,
        )
        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)


