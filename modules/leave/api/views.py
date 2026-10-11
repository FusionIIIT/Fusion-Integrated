"""REST API endpoints for ELM module - Model 2 (Qwen 14B)."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from modules.leave.models import LeaveRequest, LeaveAccount, HolidayCalendar
from modules.leave.api.serializers import LeaveRequestSerializer, LeaveAccountSerializer, HolidayCalendarSerializer
from modules.leave.selectors import leave_selectors
from modules.leave.services import leave_services


class LeaveAccountListView(APIView):
    """EL-UC-012: View employee's current leave balances."""
    def get(self, request):
        user_id = request.headers.get("X-User-Id", "fac_001")
        year = int(request.query_params.get("year", 2026))
        accounts = leave_selectors.get_user_accounts(user_id=user_id, year=year)
        serializer = LeaveAccountSerializer(accounts, many=True)
        return Response(serializer.data)


class LeaveRequestListView(APIView):
    """EL-UC-001 & EL-UC-012: Apply for leave or list user's leave requests."""
    def get(self, request):
        user_id = request.headers.get("X-User-Id", "fac_001")
        requests = leave_selectors.get_user_leave_requests(user_id=user_id)
        serializer = LeaveRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id = request.headers.get("X-User-Id", "fac_001")
        role = request.headers.get("X-User-Role", "faculty")
        d = request.data
        try:
            req = leave_services.submit_leave_request(
                applicant_id=user_id,
                applicant_role=role,
                category=d.get("category"),
                start_date=d.get("start_date"),
                end_date=d.get("end_date"),
                purpose=d.get("purpose", ""),
                is_half_day=d.get("is_half_day", False),
                half_day_type=d.get("half_day_type"),
                is_station_leave=d.get("is_station_leave", False),
                station_destination=d.get("station_destination"),
                station_address=d.get("station_address"),
                substitute_id=d.get("substitute_id"),
                unit_head_id=d.get("unit_head_id", "hod_cse"),
                sanctioning_authority_id=d.get("sanctioning_authority_id", "dean_faculty"),
            )
            return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubstituteActionView(APIView):
    """EL-UC-002: Substitute Accept or Decline."""
    def post(self, request, pk):
        sub_id = request.headers.get("X-User-Id", "sub_001")
        accept = request.data.get("accept", True)
        try:
            req = leave_services.process_substitute_response(pk, sub_id, accept)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnitHeadActionView(APIView):
    """EL-UC-003: Unit head approve/reject (CL/RH) or recommend (higher sanction)."""
    def post(self, request, pk):
        uh_id = request.headers.get("X-User-Id", "hod_cse")
        action = request.data.get("action")
        remarks = request.data.get("remarks", "")
        est_configured = request.data.get("establishment_configured", False)
        try:
            req = leave_services.review_unit_head(pk, uh_id, action, remarks, est_configured)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class EstablishmentRouteView(APIView):
    """EL-UC-004: Establishment routing."""
    def post(self, request, pk):
        est_id = request.headers.get("X-User-Id", "est_officer")
        remarks = request.data.get("remarks", "")
        try:
            req = leave_services.route_establishment(pk, est_id, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionActionView(APIView):
    """EL-UC-005: Final Sanctioning Decision."""
    def post(self, request, pk):
        sanction_id = request.headers.get("X-User-Id", "dean_faculty")
        approve = request.data.get("approve", True)
        remarks = request.data.get("remarks", "")
        try:
            req = leave_services.sanction_decision(pk, sanction_id, approve, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawRequestView(APIView):
    """EL-UC-007: Immediate withdrawal."""
    def post(self, request, pk):
        user_id = request.headers.get("X-User-Id", "fac_001")
        try:
            req = leave_services.withdraw_request(pk, user_id)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResumptionActionView(APIView):
    """EL-UC-010 & EL-UC-011: Resumption submission and review."""
    def post(self, request, pk):
        sub_action = request.data.get("action")  # 'SUBMIT' or 'REVIEW'
        user_id = request.headers.get("X-User-Id", "fac_001")
        try:
            if sub_action == "SUBMIT":
                actual_date = request.data.get("actual_date")
                notes = request.data.get("notes", "")
                req = leave_services.submit_resumption(pk, user_id, actual_date, notes)
            else:
                remarks = request.data.get("remarks", "")
                req = leave_services.review_resumption(pk, user_id, remarks)
            return Response(LeaveRequestSerializer(req).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
