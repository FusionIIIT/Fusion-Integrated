"""API views for Employee Leave Management (ELM)."""
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.core.exceptions import ValidationError
from modules.leave.models import LeaveApplication, LeaveBalance, HolidayCalendar
from modules.leave.api.serializers import LeaveApplicationSerializer, LeaveBalanceSerializer, HolidayCalendarSerializer
from modules.leave.selectors import leave_selectors
from modules.leave.services import leave_services


class LeaveBalanceListView(APIView):
    """EL-UC-012: View employee's own balances."""
    def get(self, request):
        user_id = request.headers.get("X-User-Id", "emp_001")
        year = int(request.query_params.get("year", 2026))
        balances = leave_selectors.get_employee_balances(user_id=user_id, year=year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class LeaveApplicationListView(APIView):
    """EL-UC-001 & EL-UC-012: Apply for leave or view own leave requests."""
    def get(self, request):
        user_id = request.headers.get("X-User-Id", "emp_001")
        apps = leave_selectors.get_employee_applications(applicant_id=user_id)
        serializer = LeaveApplicationSerializer(apps, many=True)
        return Response(serializer.data)

    def post(self, request):
        user_id = request.headers.get("X-User-Id", "emp_001")
        role = request.headers.get("X-User-Role", "faculty")
        data = request.data

        try:
            app = leave_services.apply_leave(
                applicant_id=user_id,
                applicant_role=role,
                category=data.get("category"),
                start_date=data.get("start_date"),
                end_date=data.get("end_date"),
                purpose=data.get("purpose", ""),
                is_half_day=data.get("is_half_day", False),
                half_day_type=data.get("half_day_type"),
                is_station_leave=data.get("is_station_leave", False),
                station_leave_destination=data.get("station_leave_destination"),
                substitute_id=data.get("substitute_id"),
                unit_head_id=data.get("unit_head_id", "hod_001"),
            )
            return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SubstituteResponseView(APIView):
    """EL-UC-002: Substitute accepts or declines."""
    def post(self, request, pk):
        substitute_id = request.headers.get("X-User-Id", "sub_001")
        accept = request.data.get("accept", True)
        try:
            app = leave_services.respond_substitute(pk, substitute_id, accept)
            return Response(LeaveApplicationSerializer(app).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class UnitHeadReviewView(APIView):
    """EL-UC-003: Review leave at Unit Head stage."""
    def post(self, request, pk):
        uh_id = request.headers.get("X-User-Id", "hod_001")
        action = request.data.get("action")  # APPROVE, REJECT, RECOMMEND, NOT_RECOMMEND
        remarks = request.data.get("remarks", "")
        try:
            app = leave_services.unit_head_review(pk, uh_id, action, remarks)
            return Response(LeaveApplicationSerializer(app).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class SanctionDecisionView(APIView):
    """EL-UC-005: Final Sanctioning Decision."""
    def post(self, request, pk):
        sanction_id = request.headers.get("X-User-Id", "dean_001")
        approve = request.data.get("approve", True)
        remarks = request.data.get("remarks", "")
        try:
            app = leave_services.final_sanction(pk, sanction_id, approve, remarks)
            return Response(LeaveApplicationSerializer(app).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class WithdrawApplicationView(APIView):
    """EL-UC-007: Immediate withdrawal."""
    def post(self, request, pk):
        user_id = request.headers.get("X-User-Id", "emp_001")
        try:
            app = leave_services.withdraw_application(pk, user_id)
            return Response(LeaveApplicationSerializer(app).data)
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
