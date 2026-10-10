from datetime import datetime
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import (
    LeavePolicy, HolidayCalendar, AcademicCalendarVacation, LeaveBalance,
    LeaveApplication, SubstituteRequest, ResumptionRequest, OfflineLeaveRecord, SLAConfig
)
from ..serializers import (
    LeavePolicySerializer, HolidayCalendarSerializer, AcademicCalendarVacationSerializer,
    LeaveBalanceSerializer, LeaveApplicationSerializer, SubstituteRequestSerializer,
    ResumptionRequestSerializer, OfflineLeaveRecordSerializer, SLAConfigSerializer
)
from ..services import ELMService, LeaveValidationError


class LeaveApplicationViewSet(viewsets.ModelViewSet):
    queryset = LeaveApplication.objects.all().order_by("-created_at")
    serializer_class = LeaveApplicationSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        applicant_id = self.request.query_params.get("applicant_id")
        status_param = self.request.query_params.get("status")
        role = self.request.query_params.get("authority_role")

        if applicant_id:
            qs = qs.filter(applicant_id=applicant_id)
        if status_param:
            qs = qs.filter(status=status_param)
        if role:
            qs = qs.filter(current_authority_role=role)
        return qs

    @action(detail=False, methods=["post"])
    def apply(self, request):
        """UC-001: Apply for Leave"""
        data = request.data
        try:
            app = ELMService.apply_for_leave(
                applicant_id=data.get("applicant_id"),
                applicant_name=data.get("applicant_name"),
                applicant_category=data.get("applicant_category", "STAFF"),
                applicant_role=data.get("applicant_role", "EMPLOYEE"),
                department=data.get("department", "General"),
                category=data.get("category"),
                start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d").date(),
                end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d").date(),
                purpose=data.get("purpose", ""),
                half_day_type=data.get("half_day_type", "NONE"),
                is_station_leave=data.get("is_station_leave", False),
                station_address=data.get("station_address", ""),
                out_of_station_start=datetime.strptime(data.get("out_of_station_start"), "%Y-%m-%d").date() if data.get("out_of_station_start") else None,
                out_of_station_end=datetime.strptime(data.get("out_of_station_end"), "%Y-%m-%d").date() if data.get("out_of_station_end") else None,
                emergency_contact=data.get("emergency_contact", ""),
                substitute_id=data.get("substitute_id"),
                substitute_name=data.get("substitute_name")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def substitute_respond(self, request):
        """UC-002: Respond to Substitute Request"""
        data = request.data
        try:
            app = ELMService.respond_to_substitute_request(
                substitute_id=data.get("substitute_id"),
                application_id=data.get("application_id"),
                action=data.get("action"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def nominate_replacement_substitute(self, request):
        """UC-019: Nominate Replacement Substitute"""
        data = request.data
        try:
            app = ELMService.nominate_replacement_substitute(
                applicant_id=data.get("applicant_id"),
                application_id=data.get("application_id"),
                new_substitute_id=data.get("new_substitute_id"),
                new_substitute_name=data.get("new_substitute_name")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def unit_head_review(self, request):
        """UC-003: Review Leave-Related Request at Unit Head"""
        data = request.data
        try:
            app = ELMService.review_unit_head(
                reviewer_id=data.get("reviewer_id"),
                reviewer_name=data.get("reviewer_name"),
                application_id=data.get("application_id"),
                outcome=data.get("outcome"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def establishment_verify(self, request):
        """UC-004: Verify and Route Higher-Sanction Request"""
        data = request.data
        try:
            app = ELMService.verify_establishment(
                actor_id=data.get("actor_id"),
                actor_name=data.get("actor_name"),
                application_id=data.get("application_id"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def final_sanction(self, request):
        """UC-005: Make Final Sanctioning Decision"""
        data = request.data
        try:
            app = ELMService.make_final_sanction_decision(
                authority_id=data.get("authority_id"),
                authority_name=data.get("authority_name"),
                authority_role=data.get("authority_role", "REGISTRAR"),
                application_id=data.get("application_id"),
                decision=data.get("decision"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def withdraw(self, request):
        """UC-007: Withdraw Pending Request"""
        data = request.data
        try:
            app = ELMService.withdraw_pending_request(
                applicant_id=data.get("applicant_id"),
                application_id=data.get("application_id"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def request_cancellation(self, request):
        """UC-008: Request Cancellation of Approved Leave"""
        data = request.data
        try:
            app = ELMService.request_cancellation(
                applicant_id=data.get("applicant_id"),
                application_id=data.get("application_id"),
                remarks=data.get("remarks", "")
            )
            serializer = self.get_serializer(app)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def submit_resumption(self, request):
        """UC-010: Submit Resumption of Duty"""
        data = request.data
        try:
            res_req = ELMService.submit_resumption(
                applicant_id=data.get("applicant_id"),
                application_id=data.get("application_id"),
                actual_resumption_date=datetime.strptime(data.get("actual_resumption_date"), "%Y-%m-%d").date(),
                remarks=data.get("remarks", "")
            )
            serializer = ResumptionRequestSerializer(res_req)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"])
    def review_resumption(self, request):
        """UC-011: Review Resumption"""
        data = request.data
        try:
            res_req = ELMService.review_resumption(
                reviewer_id=data.get("reviewer_id"),
                reviewer_name=data.get("reviewer_name"),
                application_id=data.get("application_id"),
                remarks=data.get("remarks", "")
            )
            serializer = ResumptionRequestSerializer(res_req)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=["get"])
    def print_export(self, request, pk=None):
        """UC-013: Obtain Printable/Exportable Representation"""
        app = self.get_object()
        serializer = self.get_serializer(app)
        return Response({
            "title": f"FUSION ERP - LEAVE APPLICATION #{app.id}",
            "printed_at": datetime.now().isoformat(),
            "data": serializer.data
        })


class LeaveBalanceViewSet(viewsets.ReadOnlyModelViewSet):
    """UC-012: View Leave Balances and History"""
    queryset = LeaveBalance.objects.all()
    serializer_class = LeaveBalanceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        user_id = self.request.query_params.get("user_id")
        year = self.request.query_params.get("year")
        if user_id:
            qs = qs.filter(user_id=user_id)
        if year:
            qs = qs.filter(year=year)
        return qs


class OfflineLeaveRecordViewSet(viewsets.ModelViewSet):
    """UC-016: Record Already-Sanctioned Offline Leave"""
    queryset = OfflineLeaveRecord.objects.all().order_by("-created_at")
    serializer_class = OfflineLeaveRecordSerializer

    def create(self, request, *args, **kwargs):
        data = request.data
        try:
            record = ELMService.record_offline_leave(
                admin_id=data.get("admin_id"),
                admin_name=data.get("admin_name"),
                employee_id=data.get("employee_id"),
                employee_name=data.get("employee_name"),
                category=data.get("category"),
                start_date=datetime.strptime(data.get("start_date"), "%Y-%m-%d").date(),
                end_date=datetime.strptime(data.get("end_date"), "%Y-%m-%d").date(),
                purpose=data.get("purpose", ""),
                reference=data.get("offline_sanction_reference"),
                sanctioned_by=data.get("sanctioned_by"),
                sanction_date=datetime.strptime(data.get("sanction_date"), "%Y-%m-%d").date()
            )
            serializer = self.get_serializer(record)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except LeaveValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


class AdminControlView(APIView):
    """UC-020: Event-Triggered Year-End Processing"""
    def post(self, request):
        year = int(request.data.get("year", datetime.now().year))
        processed = ELMService.execute_year_end_processing(year)
        return Response({"status": "SUCCESS", "year": year, "records_processed": processed})


class LeavePolicyViewSet(viewsets.ModelViewSet):
    """UC-014: Maintain Policy Configuration"""
    queryset = LeavePolicy.objects.all()
    serializer_class = LeavePolicySerializer


class HolidayCalendarViewSet(viewsets.ModelViewSet):
    """UC-015: Maintain and Publish Holiday/RH Calendar"""
    queryset = HolidayCalendar.objects.all().order_by("date")
    serializer_class = HolidayCalendarSerializer
