"""API views for Employee Leave Management (ELM).

Implements both authorization gates:
- HasModuleGrant("leave_module")
- HasPermission("leave_module.*")
"""
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api.serializers import (
    ApplyLeaveInputSerializer,
    CancelRequestInputSerializer,
    ExtensionRequestInputSerializer,
    HolidayCalendarSerializer,
    LeaveActionLogSerializer,
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    OfflineLeaveInputSerializer,
    ReplaceSubstituteInputSerializer,
    ResumptionInputSerializer,
    ReviewResumptionInputSerializer,
    SanctionDecisionInputSerializer,
    SubstituteResponseInputSerializer,
    UnitHeadReviewInputSerializer,
    VacationPeriodSerializer,
    YearEndProcessingInputSerializer,
)
from modules.leave.models import HolidayCalendar, VacationPeriod
from modules.leave.selectors import leave_requests as selectors
from modules.leave.services import leave_requests as services


class ApplyLeaveView(APIView):
    """EL-UC-001: Apply for Leave."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.create"),
    ]

    def post(self, request):
        ser = ApplyLeaveInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        principal = request.principal
        user_id = principal.user_id
        employee_kind = getattr(principal, "kind", "staff")
        is_director = getattr(principal, "designation", "") == "Director"

        try:
            leave_req = services.apply_leave(
                user_id=user_id,
                category=data["category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                employee_kind=employee_kind,
                half_day=data.get("half_day"),
                substitute_user_id=data.get("substitute_user_id"),
                station_leave=data.get("station_leave", False),
                station_address=data.get("station_address", ""),
                station_contact=data.get("station_contact", ""),
                station_start_date=data.get("station_start_date"),
                station_end_date=data.get("station_end_date"),
                medical_certificate_url=data.get("medical_certificate_url", ""),
                is_director=is_director,
            )
            return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class MyLeavesView(APIView):
    """EL-UC-012: View Leave History."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def get(self, request):
        user_id = request.principal.user_id
        status_filter = request.query_params.get("status")
        leaves = selectors.list_user_leave_requests(user_id=user_id, status=status_filter)
        return Response(LeaveRequestSerializer(leaves, many=True).data)


class MyBalancesView(APIView):
    """EL-UC-012: View Leave Balances."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def get(self, request):
        user_id = request.principal.user_id
        year = int(request.query_params.get("year", timezone.localdate().year))
        # Ensure balances initialized
        services.ensure_user_balances(user_id, year, getattr(request.principal, "kind", "staff"))
        balances = selectors.get_user_balances(user_id=user_id, year=year)
        return Response(LeaveBalanceSerializer(balances, many=True).data)


class LeaveDetailView(APIView):
    """View details of a leave application."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self", "leave_module.request.review"),
    ]

    def get(self, request, request_id: int):
        user_id = request.principal.user_id
        # If user owns it or has review permission
        try:
            if request.principal.has_permission("leave_module.request.review"):
                leave_req = selectors.get_leave_request_for_review(request_id)
            else:
                leave_req = selectors.get_user_leave_request(user_id, request_id)
            logs = selectors.get_audit_trail(request_id)
            data = LeaveRequestSerializer(leave_req).data
            data["action_logs"] = LeaveActionLogSerializer(logs, many=True).data
            return Response(data)
        except Exception:
            return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)


class WithdrawLeaveView(APIView):
    """EL-UC-007: Withdraw Pending Request."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = WithdrawInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.withdraw_leave(user_id, request_id, ser.validated_data.get("reason", ""))
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class CancelLeaveView(APIView):
    """EL-UC-008: Request Cancellation of Approved Leave."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = CancelRequestInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.request_cancellation(user_id, request_id, ser.validated_data["cancellation_reason"])
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ExtendLeaveView(APIView):
    """EL-UC-009: Request Extension of Ongoing Leave."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = ExtensionRequestInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            ext_req = services.request_extension(
                user_id=user_id,
                base_request_id=request_id,
                extended_end_date=ser.validated_data["extended_end_date"],
                reason=ser.validated_data["reason"],
            )
            return Response(LeaveRequestSerializer(ext_req).data, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ResumptionLeaveView(APIView):
    """EL-UC-010: Submit Resumption of Duty."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = ResumptionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.submit_resumption(
                user_id=user_id,
                request_id=request_id,
                actual_resumption_date=ser.validated_data["actual_resumption_date"],
                remarks=ser.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class SubstituteInboxView(APIView):
    """EL-UC-002: View Substitute Requests."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.substitute.respond"),
    ]

    def get(self, request):
        user_id = request.principal.user_id
        pending_only = request.query_params.get("pending") == "true"
        reqs = selectors.list_substitute_requests(user_id, pending_only=pending_only)
        return Response(LeaveRequestSerializer(reqs, many=True).data)


class SubstituteRespondView(APIView):
    """EL-UC-002: Respond to Substitute Request."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.substitute.respond"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = SubstituteResponseInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        is_director = getattr(request.principal, "designation", "") == "Director"
        try:
            req = services.respond_substitute(
                substitute_user_id=user_id,
                request_id=request_id,
                accepted=ser.validated_data["accepted"],
                remarks=ser.validated_data.get("remarks", ""),
                is_director=is_director,
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ReplaceSubstituteView(APIView):
    """EL-UC-019: Nominate Replacement Substitute."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.create"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = ReplaceSubstituteInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.replace_substitute(
                applicant_user_id=user_id,
                request_id=request_id,
                new_substitute_user_id=ser.validated_data["new_substitute_user_id"],
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ApprovalsInboxView(APIView):
    """EL-UC-003, EL-UC-004, EL-UC-005: Approvals Inbox."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.review"),
    ]

    def get(self, request):
        status_filter = request.query_params.get("status")
        reqs = selectors.list_approvals_inbox(status=status_filter)
        return Response(LeaveRequestSerializer(reqs, many=True).data)


class UnitHeadReviewView(APIView):
    """EL-UC-003: Review Leave-Related Request at Unit Head."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.review"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = UnitHeadReviewInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.review_unit_head(
                unit_head_user_id=user_id,
                request_id=request_id,
                decision=ser.validated_data["decision"],
                remarks=ser.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionDecisionView(APIView):
    """EL-UC-005: Make Final Sanctioning Decision."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.review"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = SanctionDecisionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.decide_sanction(
                sanctioning_user_id=user_id,
                request_id=request_id,
                approved=ser.validated_data["approved"],
                remarks=ser.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class ReviewResumptionView(APIView):
    """EL-UC-011: Review Resumption."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.review"),
    ]

    def post(self, request, request_id: int):
        user_id = request.principal.user_id
        ser = ReviewResumptionInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            req = services.review_resumption(
                reviewer_user_id=user_id,
                request_id=request_id,
                remarks=ser.validated_data.get("remarks", ""),
            )
            return Response(LeaveRequestSerializer(req).data)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class HolidayCalendarView(APIView):
    """EL-UC-015: Holiday & RH Calendar."""

    permission_classes = [HasModuleGrant("leave_module")]

    def get(self, request):
        year = int(request.query_params.get("year", timezone.localdate().year))
        hols = selectors.get_holiday_calendar(year)
        return Response(HolidayCalendarSerializer(hols, many=True).data)


class VacationPeriodView(APIView):
    """Vacation periods from Academic Calendar."""

    permission_classes = [HasModuleGrant("leave_module")]

    def get(self, request):
        year = int(request.query_params.get("year", timezone.localdate().year))
        vps = selectors.get_vacation_periods(year)
        return Response(VacationPeriodSerializer(vps, many=True).data)


class OfflineLeaveSyncView(APIView):
    """EL-UC-016: Record Already-Sanctioned Offline Leave."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.admin.manage"),
    ]

    def post(self, request):
        admin_id = request.principal.user_id
        ser = OfflineLeaveInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            req = services.record_offline_leave(
                admin_user_id=admin_id,
                user_id=data["user_id"],
                category=data["category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data["reason"],
                offline_reference=data["offline_reference"],
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValueError as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)


class YearEndProcessingView(APIView):
    """EL-UC-020: Execute Year-End Leave Processing."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.admin.manage"),
    ]

    def post(self, request):
        ser = YearEndProcessingInputSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        year = ser.validated_data["year"]
        results = services.execute_year_end_processing(year)
        return Response(results)


class PrintLeaveApplicationView(APIView):
    """EL-UC-013: Printable/Exportable Leave Application Record."""

    permission_classes = [
        HasModuleGrant("leave_module"),
        HasPermission("leave_module.request.view_self", "leave_module.request.review"),
    ]

    def get(self, request, request_id: int):
        user_id = request.principal.user_id
        try:
            if request.principal.has_permission("leave_module.request.review"):
                leave_req = selectors.get_leave_request_for_review(request_id)
            else:
                leave_req = selectors.get_user_leave_request(user_id, request_id)
            logs = selectors.get_audit_trail(request_id)
            balances = selectors.get_user_balances(leave_req.user_id, leave_req.start_date.year)

            record = {
                "application": LeaveRequestSerializer(leave_req).data,
                "history": LeaveActionLogSerializer(logs, many=True).data,
                "balances": LeaveBalanceSerializer(balances, many=True).data,
                "institute": "Indian Institute of Information Technology, Design and Manufacturing Jabalpur",
                "system": "Fusion ERP - Employee Leave Management System",
                "generated_at": timezone.now().isoformat(),
            }
            return Response(record)
        except Exception:
            return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)
