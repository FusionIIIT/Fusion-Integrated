"""REST API views for ELM module."""
from datetime import date
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ViewSet

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.models import (
    HolidayCalendar,
    AcademicVacationPeriod,
    LeaveBalance,
    LeaveRequest,
    LeavePolicyConfig,
)
from modules.elm.domain.validation import ValidationError
from modules.elm.selectors.leaves import (
    get_user_balances,
    get_user_leave_requests,
    get_leave_request_by_id,
    get_pending_substitute_requests,
    get_pending_unit_head_approvals,
    get_pending_sanction_approvals,
)
from modules.elm.services.leave_service import (
    initialize_user_balances,
    apply_for_leave,
    respond_substitute,
    review_unit_head,
    decide_sanction,
    withdraw_leave,
    request_cancellation,
    decide_cancellation,
    record_offline_leave,
    process_year_end_rollover,
    get_or_create_policy,
)
from modules.elm.api.serializers import (
    LeaveBalanceSerializer,
    LeaveRequestSerializer,
    LeaveRequestCreateSerializer,
    SubstituteActionSerializer,
    ApprovalActionSerializer,
    OfflineLeaveCreateSerializer,
    HolidayCalendarSerializer,
    AcademicVacationPeriodSerializer,
    PolicyConfigSerializer,
)


class BaseElmView(APIView):
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm")]


class LeaveBalanceView(BaseElmView):
    """View and initialize leave balances for the authenticated employee."""

    def get(self, request):
        user_id = request.principal.user_id
        year = int(request.query_params.get("year", date.today().year))
        balances = list(get_user_balances(user_id=user_id, year=year))

        # Auto-initialize balances for current year if none exist yet
        if not balances:
            employee_kind = getattr(request.principal, "kind", "faculty")
            balances = initialize_user_balances(
                user_id=user_id, employee_kind=employee_kind, year=year
            )

        serializer = LeaveBalanceSerializer(balances, many=True)
        return Response(serializer.data)


class LeaveRequestViewSet(ViewSet):
    """Leave application lifecycle viewset: submit, retrieve, withdraw, cancel."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm")]

    def list(self, request):
        user_id = request.principal.user_id
        requests = get_user_leave_requests(user_id=user_id)
        serializer = LeaveRequestSerializer(requests, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            leave_req = get_leave_request_by_id(int(pk))
        except LeaveRequest.DoesNotExist:
            return Response({"error": "Leave request not found"}, status=status.HTTP_404_NOT_FOUND)
        serializer = LeaveRequestSerializer(leave_req)
        return Response(serializer.data)

    def create(self, request):
        serializer = LeaveRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user_id = request.principal.user_id
        employee_kind = getattr(request.principal, "kind", "faculty")

        try:
            leave_req = apply_for_leave(
                user_id=user_id,
                employee_kind=employee_kind,
                category=data["category"],
                start_date=data["start_date"],
                end_date=data["end_date"],
                purpose=data["purpose"],
                half_day=data.get("half_day", "none"),
                is_station_leave=data.get("is_station_leave", False),
                station_address=data.get("station_address", ""),
                station_contact=data.get("station_contact", ""),
                station_start_date=data.get("station_start_date"),
                station_end_date=data.get("station_end_date"),
                substitute_user_id=data.get("substitute_user_id"),
            )
        except ValidationError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeaveRequestSerializer(leave_req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        user_id = request.principal.user_id
        remarks = request.data.get("remarks", "")
        try:
            leave_req = withdraw_leave(leave_id=int(pk), user_id=user_id, remarks=remarks)
        except (ValidationError, LeaveRequest.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave_req).data)

    @action(detail=True, methods=["post"], url_path="request-cancellation")
    def request_cancellation(self, request, pk=None):
        user_id = request.principal.user_id
        remarks = request.data.get("remarks", "")
        try:
            leave_req = request_cancellation(
                leave_id=int(pk), user_id=user_id, remarks=remarks, today=date.today()
            )
        except (ValidationError, LeaveRequest.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave_req).data)

    @action(detail=True, methods=["post"], url_path="decide-cancellation")
    def decide_cancellation(self, request, pk=None):
        actor_id = request.principal.user_id
        decision_action = request.data.get("action", "")
        remarks = request.data.get("remarks", "")
        try:
            leave_req = decide_cancellation(
                leave_id=int(pk), actor_id=actor_id, action=decision_action, remarks=remarks
            )
        except (ValidationError, LeaveRequest.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(LeaveRequestSerializer(leave_req).data)


class SubstituteQueueView(BaseElmView):
    """View and respond to pending substitute requests."""

    def get(self, request):
        user_id = request.principal.user_id
        pending = get_pending_substitute_requests(substitute_user_id=user_id)
        serializer = LeaveRequestSerializer(pending, many=True)
        return Response(serializer.data)

    def post(self, request, pk=None):
        user_id = request.principal.user_id
        serializer = SubstituteActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            leave_req = respond_substitute(
                leave_id=int(pk),
                substitute_user_id=user_id,
                action=serializer.validated_data["action"],
                remarks=serializer.validated_data.get("remarks", ""),
            )
        except (ValidationError, LeaveRequest.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeaveRequestSerializer(leave_req).data)


class ApprovalQueueView(BaseElmView):
    """Queue and actions for Unit Heads and Higher Sanctioning Authorities."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.leave.approve")]

    def get(self, request):
        queue_type = request.query_params.get("type", "unit_head")
        if queue_type == "unit_head":
            qs = get_pending_unit_head_approvals()
        else:
            qs = get_pending_sanction_approvals()
        serializer = LeaveRequestSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request, pk=None):
        actor_id = request.principal.user_id
        serializer = ApprovalActionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        target_stage = request.query_params.get("stage", "unit_head")
        try:
            if target_stage == "unit_head":
                leave_req = review_unit_head(
                    leave_id=int(pk),
                    actor_id=actor_id,
                    action=data["action"],
                    remarks=data.get("remarks", ""),
                )
            else:
                leave_req = decide_sanction(
                    leave_id=int(pk),
                    actor_id=actor_id,
                    action=data["action"],
                    remarks=data.get("remarks", ""),
                )
        except (ValidationError, LeaveRequest.DoesNotExist) as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(LeaveRequestSerializer(leave_req).data)


class AdminLeaveView(BaseElmView):
    """Admin endpoints for offline leave recording, calendars, and rollover."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    def post(self, request):
        serializer = OfflineLeaveCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        rec = record_offline_leave(
            user_id=data["user_id"],
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            offline_reference_no=data["offline_reference_no"],
            sanctioning_authority_name=data["sanctioning_authority_name"],
            sanction_date=data["sanction_date"],
            recorded_by_id=request.principal.user_id,
            remarks=data.get("remarks", ""),
        )
        return Response(
            {
                "id": rec.id,
                "offline_reference_no": rec.offline_reference_no,
                "duration_days": rec.duration_days,
                "message": "Offline leave synchronized successfully.",
            },
            status=status.HTTP_201_CREATED,
        )


class YearEndRolloverView(BaseElmView):
    """Event-triggered year-end leave balance rollover (UC-EL-020)."""
    permission_classes = [IsAuthenticatedPrincipal, HasModuleGrant("elm"), HasPermission("elm.admin.manage")]

    def post(self, request):
        target_user_id = request.data.get("user_id")
        year = int(request.data.get("year", date.today().year))
        if not target_user_id:
            return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

        res = process_year_end_rollover(user_id=int(target_user_id), year=year)
        return Response(res)


class HolidayCalendarView(BaseElmView):
    """Public calendar of institute holidays and Restricted Holidays (BR-EL-031)."""

    def get(self, request):
        year = int(request.query_params.get("year", date.today().year))
        holidays = HolidayCalendar.objects.filter(year=year, is_published=True)
        return Response(HolidayCalendarSerializer(holidays, many=True).data)


class AcademicVacationView(BaseElmView):
    """Vacation periods from Academic Calendar (EXT-01)."""

    def get(self, request):
        periods = AcademicVacationPeriod.objects.filter(is_active=True)
        return Response(AcademicVacationPeriodSerializer(periods, many=True).data)
