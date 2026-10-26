"""DRF API views for Employee Leave Management (ELM)."""
from __future__ import annotations

import datetime
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasPermission
from modules.elm.api.serializers import (
    ApplyInputSerializer,
    CancellationDecisionSerializer,
    CancellationRequestInputSerializer,
    DirectorSelfSanctionSerializer,
    EstablishmentRouteSerializer,
    ExtensionRequestInputSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationSerializer,
    LeaveBalanceSerializer,
    LeaveTypeSerializer,
    OfflineSanctionInputSerializer,
    ResumptionReviewSerializer,
    ResumptionSubmitSerializer,
    SanctionDecisionSerializer,
    SubstituteReplacementSerializer,
    SubstituteResponseSerializer,
    UnitHeadDecisionSerializer,
    YearEndProcessingInputSerializer,
)
from modules.elm.models import HolidayCalendar, LeaveApplication, LeaveType
from modules.elm.selectors.applications import (
    get_application_by_id,
    get_pending_cancellations,
    get_pending_for_director_self_sanction,
    get_pending_for_establishment,
    get_pending_for_sanction,
    get_pending_for_unit_head,
    get_pending_resumptions,
    get_pending_substitute_requests,
    get_user_applications,
)
from modules.elm.selectors.balances import get_employee_balances, list_active_leave_types
from modules.elm.selectors.calendar import get_published_holidays
from modules.elm.services.admin_ops import execute_year_end_processing, record_offline_leave
from modules.elm.services.apply import apply_for_leave
from modules.elm.services.cancellation import decide_cancellation, request_cancellation
from modules.elm.services.extension import request_extension
from modules.elm.services.resumption import review_resumption, submit_resumption
from modules.elm.services.review import (
    decide_sanction,
    review_unit_head,
    route_establishment,
    self_sanction_director,
)
from modules.elm.services.substitute import (
    nominate_replacement_substitute,
    respond_to_substitute,
)
from modules.elm.services.withdraw import withdraw_pending_request


class LeaveTypeListView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveTypeSerializer(many=True))
    def get(self, request):
        types = list_active_leave_types()
        serializer = LeaveTypeSerializer(types, many=True)
        return Response(serializer.data)


class MyApplicationsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        applications = get_user_applications(request.user.user_id)
        serializer = LeaveApplicationSerializer(applications, many=True)
        return Response(serializer.data)

    @extend_schema(request=ApplyInputSerializer, responses=LeaveApplicationSerializer)
    def post(self, request):
        serializer = ApplyInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        is_faculty = getattr(request.user, "is_faculty", False)
        is_director = "Director" in getattr(request.user, "roles", [])

        app = apply_for_leave(
            actor=request.user,
            leave_type_id=data["leave_type"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            is_half_day=data["is_half_day"],
            half_day_period=data["half_day_period"],
            is_station_leave=data["is_station_leave"],
            station_destination=data.get("station_destination", ""),
            station_start_date=data.get("station_start_date"),
            station_end_date=data.get("station_end_date"),
            station_address=data.get("station_address", ""),
            station_contact_no=data.get("station_contact_no", ""),
            substitute_id=data.get("substitute_id"),
            is_faculty=is_faculty,
            is_director=is_director,
        )
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def get(self, request, pk):
        app = get_application_by_id(pk)
        if not app:
            raise NotFoundError("Application not found.", code="not_found")
        return Response(LeaveApplicationSerializer(app).data)


class WithdrawView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.withdraw")]

    @extend_schema(responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        app = withdraw_pending_request(request.user, pk)
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteTasksView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.substitute.respond")]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        tasks = get_pending_substitute_requests(request.user.user_id)
        return Response(LeaveApplicationSerializer(tasks, many=True).data)


class SubstituteRespondView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.substitute.respond")]

    @extend_schema(request=SubstituteResponseSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = SubstituteResponseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = respond_to_substitute(
            actor=request.user,
            application_id=pk,
            accept=serializer.validated_data["accept"],
            declined_reason=serializer.validated_data.get("declined_reason", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteReplaceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.apply")]

    @extend_schema(request=SubstituteReplacementSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = SubstituteReplacementSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = nominate_replacement_substitute(
            actor=request.user,
            application_id=pk,
            new_substitute_id=serializer.validated_data["new_substitute_id"],
        )
        return Response(LeaveApplicationSerializer(app).data)


class PendingApprovalsView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.unit_head.review")]

    def get(self, request):
        user_roles = getattr(request.user, "roles", [])
        data = {
            "unit_head": LeaveApplicationSerializer(get_pending_for_unit_head(request.user.user_id), many=True).data,
            "cancellations": LeaveApplicationSerializer([c.application for c in get_pending_cancellations()], many=True).data,
            "resumptions": LeaveApplicationSerializer([r.application for r in get_pending_resumptions()], many=True).data,
        }
        if "Deputy Registrar (Estt.)" in user_roles or "Leave Admin" in user_roles:
            data["establishment"] = LeaveApplicationSerializer(get_pending_for_establishment(), many=True).data
        if any(r in user_roles for r in ["Dean", "Registrar", "Director"]):
            data["sanction"] = LeaveApplicationSerializer(get_pending_for_sanction(request.user.user_id), many=True).data
        if "Director" in user_roles:
            data["director_self_sanction"] = LeaveApplicationSerializer(get_pending_for_director_self_sanction(request.user.user_id), many=True).data

        return Response(data)


class UnitHeadReviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.unit_head.review")]

    @extend_schema(request=UnitHeadDecisionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = UnitHeadDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = review_unit_head(
            actor=request.user,
            application_id=pk,
            outcome=serializer.validated_data["outcome"],
            remarks=serializer.validated_data.get("remarks", ""),
            has_establishment_step=serializer.validated_data.get("has_establishment_step", False),
        )
        return Response(LeaveApplicationSerializer(app).data)


class EstablishmentRouteView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.establishment.route")]

    @extend_schema(request=EstablishmentRouteSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = EstablishmentRouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = route_establishment(
            actor=request.user,
            application_id=pk,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SanctionDecideView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.sanction.decide")]

    @extend_schema(request=SanctionDecisionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = SanctionDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = decide_sanction(
            actor=request.user,
            application_id=pk,
            approve=serializer.validated_data["approve"],
            sanctioning_role=serializer.validated_data.get("sanctioning_role", "Dean"),
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class DirectorSelfSanctionView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.director.self_sanction")]

    @extend_schema(request=DirectorSelfSanctionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk):
        serializer = DirectorSelfSanctionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        app = self_sanction_director(
            actor=request.user,
            application_id=pk,
            approve=serializer.validated_data["approve"],
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class CancellationRequestView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.cancel")]

    @extend_schema(request=CancellationRequestInputSerializer)
    def post(self, request, pk):
        serializer = CancellationRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancel_req = request_cancellation(
            actor=request.user,
            application_id=pk,
            reason=serializer.validated_data["reason"],
        )
        return Response({"id": cancel_req.id, "status": cancel_req.status}, status=status.HTTP_201_CREATED)


class CancellationDecideView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.unit_head.review")]

    @extend_schema(request=CancellationDecisionSerializer)
    def post(self, request, pk):
        serializer = CancellationDecisionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        cancel_req = decide_cancellation(
            actor=request.user,
            cancellation_id=pk,
            approve=serializer.validated_data["approve"],
            remarks=serializer.validated_data.get("remarks", ""),
            is_final_authority=serializer.validated_data.get("is_final_authority", False),
        )
        return Response({"id": cancel_req.id, "status": cancel_req.status})


class ExtensionRequestView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.apply")]

    @extend_schema(request=ExtensionRequestInputSerializer)
    def post(self, request, pk):
        serializer = ExtensionRequestInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ext = request_extension(
            actor=request.user,
            application_id=pk,
            new_end_date=serializer.validated_data["new_end_date"],
            reason=serializer.validated_data["reason"],
            substitute_id=serializer.validated_data.get("substitute_id"),
        )
        return Response({"id": ext.id, "days": float(ext.days), "status": ext.status}, status=status.HTTP_201_CREATED)


class ResumptionSubmitView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.application.view")]

    @extend_schema(request=ResumptionSubmitSerializer)
    def post(self, request, pk):
        serializer = ResumptionSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rep = submit_resumption(
            actor=request.user,
            application_id=pk,
            actual_resumption_date=serializer.validated_data["actual_resumption_date"],
            reason_for_difference=serializer.validated_data.get("reason_for_difference", ""),
        )
        return Response({"id": rep.id, "resumption_type": rep.resumption_type, "status": rep.status}, status=status.HTTP_201_CREATED)


class ResumptionReviewView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.sanction.decide")]

    @extend_schema(request=ResumptionReviewSerializer)
    def post(self, request, pk):
        serializer = ResumptionReviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rep = review_resumption(
            actor=request.user,
            resumption_id=pk,
            remarks=serializer.validated_data.get("remarks", ""),
        )
        return Response({"id": rep.id, "status": rep.status})


class MyBalanceView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.balance.view")]

    @extend_schema(responses=LeaveBalanceSerializer(many=True))
    def get(self, request):
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else timezone.localtime().year
        balances = get_employee_balances(request.user.user_id, year=year)
        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class HolidayCalendarView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.calendar.view")]

    @extend_schema(responses=HolidayCalendarSerializer(many=True))
    def get(self, request):
        year_str = request.query_params.get("year")
        year = int(year_str) if year_str and year_str.isdigit() else timezone.localtime().year
        holidays = get_published_holidays(year)
        serializer = HolidayCalendarSerializer(holidays, many=True)
        return Response(serializer.data)


class OfflineSanctionView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.admin.sync_offline")]

    @extend_schema(request=OfflineSanctionInputSerializer)
    def post(self, request):
        serializer = OfflineSanctionInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        rec = record_offline_leave(
            actor=request.user,
            employee_id=d["employee_id"],
            leave_type_id=d["leave_type_id"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            sanction_order_no=d["sanction_order_no"],
            sanction_order_date=d["sanction_order_date"],
            sanctioned_by_role=d["sanctioned_by_role"],
            remarks=d.get("remarks", ""),
        )
        return Response({"id": rec.id, "days": float(rec.days)}, status=status.HTTP_201_CREATED)


class YearEndProcessingView(APIView):
    permission_classes = [IsAuthenticated, HasPermission("leave_elm.admin.year_end")]

    @extend_schema(request=YearEndProcessingInputSerializer)
    def post(self, request):
        serializer = YearEndProcessingInputSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        d = serializer.validated_data
        res = execute_year_end_processing(
            employee_ids=d.get("employee_ids", []),
            old_year=d["old_year"],
            new_year=d["new_year"],
            faculty_user_ids=set(d.get("faculty_user_ids", [])),
        )
        return Response(res)
