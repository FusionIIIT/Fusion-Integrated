"""Views for Employee Leave Management API endpoints."""
from __future__ import annotations

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api import serializers as s
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)
from modules.elm.selectors.applications import (
    approval_queue,
    visible_applications,
    visible_balances,
)
from modules.elm.services.application_service import (
    apply_leave,
    nominate_replacement_substitute,
    respond_substitute,
    review_leave,
    withdraw_leave,
)
from modules.elm.services.cancellation_service import (
    request_cancellation,
    review_cancellation,
)
from modules.elm.services.extension_service import request_extension
from modules.elm.services.offline_leave_service import record_offline_sanctioned_leave
from modules.elm.services.resumption_service import (
    review_duty_resumption,
    submit_duty_resumption,
)
from modules.elm.services.rollover_service import execute_year_end_rollover

MODULE_GATE = HasModuleGrant("leave_elm")


def _principal_user_id(request) -> int:
    principal = getattr(request, "principal", None)
    return int(getattr(principal, "user_id", getattr(principal, "id", 0)) or 0)


def _is_director(request) -> bool:
    principal = getattr(request, "principal", None)
    if not principal:
        return False
    roles = getattr(principal, "roles", ()) or ()
    active_role = getattr(principal, "active_role", "") or ""
    return "Director" in roles or active_role == "Director"


class LeaveTypeListView(generics.ListAPIView):
    serializer_class = s.LeaveTypeSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.application.view")]
    queryset = LeaveType.objects.filter(is_active=True)


class LeaveBalanceListView(generics.ListAPIView):
    serializer_class = s.LeaveBalanceSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.balance.view")]
    queryset = LeaveBalance.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveBalance.objects.none()
        target_uid = self.request.query_params.get("user_id")
        year = self.request.query_params.get("year")
        uid_int = int(target_uid) if target_uid and target_uid.isdigit() else None
        year_int = int(year) if year and year.isdigit() else None
        return visible_balances(
            self.request.principal, target_user_id=uid_int, year=year_int
        )


class LeaveApplicationListCreateView(generics.ListCreateAPIView):
    serializer_class = s.LeaveApplicationSerializer
    queryset = LeaveApplication.objects.none()

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE_GATE(), HasPermission("leave_elm.application.apply")()]
        return [MODULE_GATE(), HasPermission("leave_elm.application.view")()]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        return visible_applications(self.request.principal)

    def create(self, request, *args, **kwargs):
        inp = s.LeaveApplicationCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        data = inp.validated_data
        try:
            app = apply_leave(
                user_id=_principal_user_id(request),
                leave_type_code=data["leave_type_code"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                half_day=data.get("half_day", False),
                station_leave=data.get("station_leave", False),
                station_address=data.get("station_address", ""),
                reason=data.get("reason", ""),
                substitute_user_id=data.get("substitute_user_id"),
                is_director=_is_director(request),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveWithdrawView(APIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.withdraw"),
    ]

    def post(self, request, pk: int):
        try:
            app = withdraw_leave(
                application_id=pk,
                applicant_user_id=_principal_user_id(request),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteResponseView(APIView):
    serializer_class = s.SubstituteDecisionSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.substitute.respond"),
    ]

    def post(self, request, pk: int):
        inp = s.SubstituteDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        decision = inp.validated_data["decision"]
        try:
            app = respond_substitute(
                application_id=pk,
                substitute_user_id=_principal_user_id(request),
                decision=decision,
                is_director=_is_director(request),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class SubstituteReplacementView(APIView):
    serializer_class = s.SubstituteReplacementSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.apply"),
    ]

    def post(self, request, pk: int):
        inp = s.SubstituteReplacementSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        try:
            app = nominate_replacement_substitute(
                application_id=pk,
                applicant_user_id=_principal_user_id(request),
                substitute_user_id=inp.validated_data["substitute_user_id"],
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveApprovalQueueView(generics.ListAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.approve"),
    ]
    queryset = LeaveApplication.objects.none()

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return LeaveApplication.objects.none()
        return approval_queue(self.request.principal)


class LeaveApprovalDecisionView(APIView):
    serializer_class = s.LeaveDecisionSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.approve"),
    ]

    def post(self, request, pk: int):
        inp = s.LeaveDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        decision = inp.validated_data["decision"]
        remarks = inp.validated_data.get("remarks", "")
        try:
            app = review_leave(
                application_id=pk,
                reviewer_user_id=_principal_user_id(request),
                decision=decision,
                remarks=remarks,
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveCancellationRequestView(APIView):
    serializer_class = s.LeaveCancellationRequestSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.application.cancel"),
    ]

    def post(self, request, pk: int):
        inp = s.LeaveCancellationRequestSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        try:
            app = request_cancellation(
                application_id=pk,
                applicant_user_id=_principal_user_id(request),
                reason=inp.validated_data["reason"],
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveCancellationDecisionView(APIView):
    serializer_class = s.LeaveCancellationDecisionSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.cancellation.review"),
    ]

    def post(self, request, pk: int):
        inp = s.LeaveCancellationDecisionSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        decision = inp.validated_data["decision"]
        remarks = inp.validated_data.get("remarks", "")
        try:
            app = review_cancellation(
                application_id=pk,
                reviewer_user_id=_principal_user_id(request),
                decision=decision,
                remarks=remarks,
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class LeaveExtensionCreateView(APIView):
    serializer_class = s.LeaveExtensionCreateSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.extension.apply"),
    ]

    def post(self, request, pk: int):
        inp = s.LeaveExtensionCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        data = inp.validated_data
        try:
            app = request_extension(
                original_application_id=pk,
                applicant_user_id=_principal_user_id(request),
                start_date=data["start_date"],
                end_date=data["end_date"],
                reason=data.get("reason", ""),
                substitute_user_id=data.get("substitute_user_id"),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class DutyResumptionSubmitView(APIView):
    serializer_class = s.DutyResumptionSubmitSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.resumption.submit"),
    ]

    def post(self, request, pk: int):
        inp = s.DutyResumptionSubmitSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        data = inp.validated_data
        try:
            app = submit_duty_resumption(
                application_id=pk,
                user_id=_principal_user_id(request),
                actual_resumption_date=data["actual_resumption_date"],
                remarks=data.get("remarks", ""),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class DutyResumptionReviewView(APIView):
    serializer_class = s.DutyResumptionReviewSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.resumption.review"),
    ]

    def post(self, request, pk: int):
        inp = s.DutyResumptionReviewSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        remarks = inp.validated_data.get("remarks", "")
        try:
            app = review_duty_resumption(
                application_id=pk,
                reviewer_user_id=_principal_user_id(request),
                remarks=remarks,
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data)


class OfflineLeaveCreateListView(generics.ListCreateAPIView):
    serializer_class = s.LeaveApplicationSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.offline.record"),
    ]

    def get_queryset(self):
        return LeaveApplication.objects.filter(is_offline=True).select_related("leave_type")

    def create(self, request, *args, **kwargs):
        inp = s.OfflineLeaveCreateSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        data = inp.validated_data
        try:
            app = record_offline_sanctioned_leave(
                user_id=data["user_id"],
                leave_type_code=data["leave_type_code"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                sanction_reference=data["sanction_reference"],
                sanction_date=data["sanction_date"],
                sanction_authority_name=data["sanction_authority_name"],
                reason=data.get("reason", ""),
                recorder_user_id=_principal_user_id(request),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(s.LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class LeaveRolloverExecuteView(APIView):
    serializer_class = s.LeaveRolloverExecuteSerializer
    permission_classes = [
        MODULE_GATE,
        HasPermission("leave_elm.rollover.execute"),
    ]

    def post(self, request):
        inp = s.LeaveRolloverExecuteSerializer(data=request.data)
        inp.is_valid(raise_exception=True)
        target_year = inp.validated_data["target_year"]
        try:
            records = execute_year_end_rollover(
                target_year=target_year,
                executor_user_id=_principal_user_id(request),
            )
        except ValueError as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            s.LeaveRolloverRecordSerializer(records, many=True).data,
            status=status.HTTP_200_OK,
        )


class HolidayCalendarListView(generics.ListAPIView):
    serializer_class = s.HolidayCalendarSerializer
    permission_classes = [MODULE_GATE, HasPermission("leave_elm.calendar.view")]
    queryset = HolidayCalendar.objects.all()
