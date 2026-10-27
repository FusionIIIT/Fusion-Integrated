"""API views for Employee Leave Management."""
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ViewSet

from fusion_auth.permissions import HasModuleGrant, HasPermission, IsAuthenticatedPrincipal
from modules.elm.api.serializers import (
    LeaveAccountSerializer,
    LeaveRequestCreateSerializer,
    LeaveRequestSerializer,
    OfflineLeaveSerializer,
    ReviewActionSerializer,
    SubstituteResponseSerializer,
)
from modules.elm.models import LeaveAccount, LeaveRequest, LeaveStatus
from modules.elm.services.admin import (
    execute_year_end_processing,
    process_sla_sweep,
    record_offline_leave,
)
from modules.elm.services.workflow import (
    request_cancellation,
    respond_substitute,
    review_cancellation,
    sanction_review,
    submit_leave_request,
    unit_head_review,
    withdraw_request,
)

MODULE_GRANT = HasModuleGrant("elm")


class LeaveRequestViewSet(ModelViewSet):
    permission_classes = [IsAuthenticatedPrincipal, MODULE_GRANT]
    serializer_class = LeaveRequestSerializer

    def get_queryset(self):
        p = getattr(self.request, "principal", None)
        user_id = p.user_id if p else None
        # Default: list applicant's own requests
        return LeaveRequest.objects.filter(applicant_id=user_id)

    def create(self, request, *args, **kwargs):
        ser = LeaveRequestCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        p = getattr(request, "principal", None)
        applicant_id = p.user_id if p else 1
        employee_kind = getattr(p, "kind", "faculty")
        is_director = "director" in getattr(p, "roles", [])

        req = submit_leave_request(
            applicant_id=applicant_id,
            employee_kind=employee_kind,
            category=data["category"],
            start_date=data["start_date"],
            end_date=data["end_date"],
            reason=data["reason"],
            substitute_id=data.get("substitute_id"),
            is_half_day=data.get("is_half_day", False),
            half_day_type=data.get("half_day_type"),
            is_station_leave=data.get("is_station_leave", False),
            station_address=data.get("station_address", ""),
            emergency_contact=data.get("emergency_contact", ""),
            is_director=is_director,
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], url_path="withdraw")
    def withdraw(self, request, pk=None):
        p = getattr(request, "principal", None)
        applicant_id = p.user_id if p else 1
        req = withdraw_request(request_id=int(pk), applicant_id=applicant_id)
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="cancel")
    def cancel(self, request, pk=None):
        p = getattr(request, "principal", None)
        applicant_id = p.user_id if p else 1
        req = request_cancellation(request_id=int(pk), applicant_id=applicant_id)
        return Response(LeaveRequestSerializer(req).data)


class SubstituteViewSet(ViewSet):
    permission_classes = [IsAuthenticatedPrincipal, MODULE_GRANT, HasPermission("elm.leave.substitute")]

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        p = getattr(request, "principal", None)
        user_id = p.user_id if p else 1
        reqs = LeaveRequest.objects.filter(
            substitute_assignments__substitute_id=user_id,
            substitute_assignments__status="PENDING",
            status=LeaveStatus.AWAITING_SUBSTITUTE_RESPONSE,
        )
        return Response(LeaveRequestSerializer(reqs, many=True).data)

    @action(detail=True, methods=["post"], url_path="respond")
    def respond(self, request, pk=None):
        ser = SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        p = getattr(request, "principal", None)
        substitute_id = p.user_id if p else 1

        req = respond_substitute(
            request_id=int(pk),
            substitute_id=substitute_id,
            accept=ser.validated_data["accept"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(req).data)


class ApprovalQueueViewSet(ViewSet):
    permission_classes = [IsAuthenticatedPrincipal, MODULE_GRANT, HasPermission("elm.leave.unit_head_review", "elm.leave.sanction")]

    @action(detail=False, methods=["get"], url_path="pending")
    def pending(self, request):
        pending_states = [
            LeaveStatus.AWAITING_UNIT_HEAD_REVIEW,
            LeaveStatus.AWAITING_ESTABLISHMENT_REVIEW,
            LeaveStatus.AWAITING_SANCTION_AUTHORITY_REVIEW,
        ]
        reqs = LeaveRequest.objects.filter(status__in=pending_states)
        return Response(LeaveRequestSerializer(reqs, many=True).data)

    @action(detail=True, methods=["post"], url_path="unit-head-review")
    def unit_head(self, request, pk=None):
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        req = unit_head_review(
            request_id=int(pk),
            action=ser.validated_data["action"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(req).data)

    @action(detail=True, methods=["post"], url_path="sanction")
    def sanction(self, request, pk=None):
        ser = ReviewActionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        approve = ser.validated_data["action"].upper() == "APPROVE"
        req = sanction_review(
            request_id=int(pk),
            approve=approve,
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveRequestSerializer(req).data)


class BalanceViewSet(ViewSet):
    permission_classes = [IsAuthenticatedPrincipal, MODULE_GRANT, HasPermission("elm.leave.view_self")]

    def list(self, request):
        p = getattr(request, "principal", None)
        user_id = p.user_id if p else 1
        accounts = LeaveAccount.objects.filter(employee_id=user_id)
        return Response(LeaveAccountSerializer(accounts, many=True).data)


class AdminOperationsViewSet(ViewSet):
    permission_classes = [IsAuthenticatedPrincipal, MODULE_GRANT, HasPermission("elm.leave.admin")]

    @action(detail=False, methods=["post"], url_path="offline-record")
    def offline_record(self, request):
        ser = OfflineLeaveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        d = ser.validated_data
        req = record_offline_leave(
            employee_id=d["employee_id"],
            category=d["category"],
            start_date=d["start_date"],
            end_date=d["end_date"],
            sanction_reference=d["sanction_reference"],
            reason=d["reason"],
            is_station_leave=d.get("is_station_leave", False),
            station_address=d.get("station_address", ""),
        )
        return Response(LeaveRequestSerializer(req).data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], url_path="sla-sweep")
    def sla_sweep(self, request):
        res = process_sla_sweep()
        return Response(res)
