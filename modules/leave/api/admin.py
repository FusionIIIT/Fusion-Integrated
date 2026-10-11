"""Leave records and ELM configuration.

Two different authorities live here and they are deliberately separate:

    leave.balance.update  adjust a balance, synchronise an offline sanction,
                          correct a recorded value — never a decision
    leave.type.manage     policy parameters, the hierarchy, the holiday/RH
                          calendar and the SLA thresholds

Reading is `leave.request.view`, the same grant the records screen uses.
"""
from __future__ import annotations

import logging

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.leave.api import serializers as s
from modules.leave.models import HolidayCalendar, LeavePolicy, SlaThreshold
from modules.leave.selectors import leave as sel
from modules.leave.services import config as config_service
from modules.leave.services import records as records_service

log = logging.getLogger("fusion.leave.api.admin")

MODULE = HasModuleGrant("leave")
P_VIEW = "leave.request.view"
P_BALANCE = "leave.balance.update"
P_CONFIGURE = "leave.type.manage"


def _actor(request):
    return getattr(request, "principal", None)


# -- Records -------------------------------------------------------------------
@extend_schema(responses=s.LeaveRequestSerializer(many=True))
class LeaveRecordsView(APIView):
    """Every leave record, within the caller's visible scope (EL-UC-017)."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request):
        rows = sel.requests_for(_actor(request))
        category = request.query_params.get("category")
        status_filter = request.query_params.get("status")
        user_id = request.query_params.get("user_id")
        if category:
            rows = rows.filter(category=category)
        if status_filter:
            rows = rows.filter(status=status_filter)
        if user_id:
            try:
                rows = rows.filter(user_id=int(user_id))
            except (TypeError, ValueError) as exc:
                raise BadRequestError("user_id must be a number.",
                                      code="invalid_user_id") from exc
        return Response({"results": s.LeaveRequestSerializer(
            rows.order_by("-created_at")[:200], many=True).data})


@extend_schema(responses=s.LeaveBalanceSerializer(many=True))
class LeaveBalanceDetailView(APIView):
    """An employee's leave account, as the office sees it."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, user_id: int):
        year = request.query_params.get("leave_year")
        rows = sel.balances_of(user_id, int(year) if year else None)
        return Response({"user_id": user_id,
                         "results": s.LeaveBalanceSerializer(rows, many=True).data})


@extend_schema(responses=s.LedgerEntrySerializer(many=True))
class LeaveLedgerView(APIView):
    """Account transactions: why a balance is what it is."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, user_id: int):
        year = request.query_params.get("leave_year")
        rows = sel.ledger_for(user_id, int(year) if year else None)[:500]
        return Response({"results": s.LedgerEntrySerializer(rows, many=True).data})


@extend_schema(request=s.OfflineRecordSerializer,
               responses={201: s.LeaveRequestSerializer})
class OfflineRecordView(APIView):
    """EL-UC-016 — synchronise leave already sanctioned outside ELM.

    Record synchronisation, not a second approval: there is no approval
    workflow behind this endpoint (BR-EL-029).
    """

    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    def post(self, request):
        payload = s.OfflineRecordSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = records_service.record_offline(actor=_actor(request),
                                              **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave).data, status=201)


@extend_schema(request=s.BalanceAdjustmentSerializer,
               responses=s.LeaveBalanceSerializer)
class BalanceAdjustmentView(APIView):
    """EL-UC-017 — an authorised balance correction."""

    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    def post(self, request):
        payload = s.BalanceAdjustmentSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        balance = records_service.adjust_balance(actor=_actor(request),
                                                **payload.validated_data)
        return Response(s.LeaveBalanceSerializer(balance).data)


@extend_schema(request=s.RecordCorrectionSerializer,
               responses=s.LeaveRequestSerializer)
class RecordCorrectionView(APIView):
    """EL-UC-017 — correct a recorded value, keeping before and after."""

    permission_classes = [MODULE, HasPermission(P_BALANCE)]

    def post(self, request, pk: int):
        payload = s.RecordCorrectionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        leave = records_service.correct_request(actor=_actor(request),
                                               request_id=pk,
                                               **payload.validated_data)
        return Response(s.LeaveRequestSerializer(leave).data)


@extend_schema(responses=s.RecordAdjustmentSerializer(many=True))
class RecordAdjustmentsView(APIView):
    """The maintenance history of one record."""

    permission_classes = [MODULE, HasPermission(P_VIEW)]

    def get(self, request, pk: int):
        leave = sel.request_for(_actor(request), pk)
        if leave is None:
            raise NotFoundError("No such leave record.")
        rows = leave.adjustments.all()[:200]
        return Response({"results": s.RecordAdjustmentSerializer(rows, many=True).data})


# -- Configuration -------------------------------------------------------------
@extend_schema(request=s.PolicyWriteSerializer,
               responses=s.LeavePolicySerializer)
class PolicyView(APIView):
    """EL-UC-014 — the current leave-policy parameters."""

    permission_classes = [MODULE, HasPermission(P_CONFIGURE)]

    @extend_schema(responses=s.LeavePolicySerializer(many=True))
    def get(self, request):
        rows = LeavePolicy.objects.all()[:50]
        return Response({"results": s.LeavePolicySerializer(rows, many=True).data})

    def put(self, request):
        payload = s.PolicyWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        policy = config_service.save_policy(actor=_actor(request),
                                            **payload.validated_data)
        return Response(s.LeavePolicySerializer(policy).data)


@extend_schema(request=s.HierarchyReplaceSerializer, responses={200: dict})
class HierarchyView(APIView):
    """EL-UC-014 — the hierarchy the routing is resolved from (BR-EL-019)."""

    permission_classes = [MODULE, HasPermission(P_CONFIGURE)]

    def get(self, request):
        return Response({"results": sel.hierarchy_rules()})

    def put(self, request):
        payload = s.HierarchyReplaceSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        steps = config_service.replace_hierarchy(
            actor=_actor(request), category=payload.validated_data["category"],
            steps=payload.validated_data["steps"])
        return Response({"replaced": len(steps),
                         "category": payload.validated_data["category"]})


@extend_schema(request=s.CalendarWriteSerializer,
               responses=s.HolidayCalendarSerializer)
class CalendarView(APIView):
    """EL-UC-015 — create or revise the holiday/RH calendar."""

    permission_classes = [MODULE, HasPermission(P_CONFIGURE)]

    @extend_schema(responses=s.HolidayCalendarSerializer(many=True))
    def get(self, request):
        rows = HolidayCalendar.objects.prefetch_related("entries")[:20]
        return Response({"results": s.HolidayCalendarSerializer(rows, many=True).data})

    def post(self, request):
        payload = s.CalendarWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        calendar = config_service.save_calendar(actor=_actor(request),
                                                **payload.validated_data)
        return Response(s.HolidayCalendarSerializer(calendar).data)


@extend_schema(request=None, responses=s.HolidayCalendarSerializer)
class CalendarPublishView(APIView):
    """EL-UC-015 M3/M4 — publishing makes this the governing calendar."""

    permission_classes = [MODULE, HasPermission(P_CONFIGURE)]

    def post(self, request, pk: int):
        calendar = config_service.publish_calendar(actor=_actor(request),
                                                   calendar_id=pk)
        return Response(s.HolidayCalendarSerializer(calendar).data)


@extend_schema(request=s.SlaThresholdWriteSerializer,
               responses=s.SlaThresholdSerializer)
class SlaThresholdView(APIView):
    """EL-UC-018 — reminder and escalation thresholds (BR-EL-038)."""

    permission_classes = [MODULE, HasPermission(P_CONFIGURE)]

    @extend_schema(responses=s.SlaThresholdSerializer(many=True))
    def get(self, request):
        rows = SlaThreshold.objects.all()[:100]
        return Response({"results": s.SlaThresholdSerializer(rows, many=True).data})

    def put(self, request):
        payload = s.SlaThresholdWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        threshold = config_service.save_thresholds(actor=_actor(request),
                                                  **payload.validated_data)
        return Response(s.SlaThresholdSerializer(threshold).data)
