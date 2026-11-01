"""HTTP layer: parse, scope, delegate, serialise.

Two gates on every endpoint — the module grant, then the permission — and the
service re-checks the permission, the duty roster and self-decision on every
write. Querysets come from `selectors.scoping`, so a row out of scope is a 404.
"""
from __future__ import annotations

from datetime import date, timedelta

from django.db.models import F
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError, NotFoundError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.visitor_hostel.api import serializers as s
from modules.visitor_hostel.domain import duty
from modules.visitor_hostel.domain import permissions as perms
from modules.visitor_hostel.domain import state_machine as sm
from modules.visitor_hostel.models import (
    DutyAssignment,
    MealTariff,
    ModificationRequest,
    Room,
    RoomTariff,
)
from modules.visitor_hostel.selectors import reports, scoping
from modules.visitor_hostel.selectors import rooms as room_selectors
from modules.visitor_hostel.services import billing as billing_service
from modules.visitor_hostel.services import bookings as booking_service
from modules.visitor_hostel.services import configuration as config_service
from modules.visitor_hostel.services import inventory as inventory_service

MODULE = HasModuleGrant(perms.MODULE)
REQUISITION_FIELDS = tuple(s.RequisitionSerializer().fields)


def _actor(request):
    return getattr(request, "principal", None)


def _date_param(params, name, default: date) -> date:
    """An unparseable date is a 400, never a 500."""
    raw = params.get(name)
    if raw in (None, ""):
        return default
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise BadRequestError(f"{name} must be a date (YYYY-MM-DD).",
                              code="invalid_filter") from exc


def _range(request, default_days=30) -> tuple[date, date]:
    today = timezone.localdate()
    start = _date_param(request.query_params, "from", today - timedelta(days=default_days))
    end = _date_param(request.query_params, "to", today)
    if end < start:
        raise BadRequestError("'to' must be on or after 'from'.", code="invalid_filter")
    if (end - start).days > 366:
        raise BadRequestError("A report covers at most one year.", code="invalid_filter")
    return start, end


def _detail(actor, pk):
    return s.BookingDetailSerializer(
        scoping.bookings_detailed(actor).get(pk=pk)).data


# -- Bookings ------------------------------------------------------------------
@extend_schema(request=s.RequisitionSerializer, responses=s.BookingSerializer,
               parameters=[OpenApiParameter("status", str), OpenApiParameter("offline", bool)])
class BookingListView(generics.ListCreateAPIView):
    """GET: own bookings for an Indenter, all for the Caretaker / In-Charge.
    POST: UC-VH-001, an online requisition."""

    serializer_class = s.BookingSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission(perms.BOOKING_CREATE)()]
        return [MODULE(), HasPermission(perms.BOOKING_VIEW_SELF,
                                        *scoping.OPERATOR_BOOKING_PERMISSIONS)()]

    def get_queryset(self):
        qs = scoping.bookings_for(_actor(self.request))
        state = self.request.query_params.get("status")
        if state:
            if state not in sm.ALL_STATES:
                raise BadRequestError("Unknown status.", code="invalid_filter")
            qs = qs.filter(status=state)
        offline = self.request.query_params.get("offline")
        if offline in ("true", "false"):
            qs = qs.filter(is_offline=offline == "true")
        return qs.order_by("-created_at")

    def create(self, request, *args, **kwargs):
        payload = s.RequisitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        booking = booking_service.submit_online(actor=_actor(request),
                                                data=payload.validated_data)
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.OfflineRequisitionSerializer, responses=s.BookingSerializer)
class OfflineBookingView(APIView):
    """UC-VH-005."""

    permission_classes = [MODULE, HasPermission(perms.OFFLINE_BOOKING_CREATE)]

    def post(self, request):
        payload = s.OfflineRequisitionSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = dict(payload.validated_data)
        booking = booking_service.record_offline(
            actor=_actor(request), source=data.pop("source"),
            indenter_user_id=data.pop("indenter_user_id", None), data=data)
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


@extend_schema(responses=s.BookingDetailSerializer)
class BookingDetailView(generics.RetrieveAPIView):
    """UC-VH-002: status, history and confirmation details, printable."""

    serializer_class = s.BookingDetailSerializer
    permission_classes = [MODULE, HasPermission(perms.BOOKING_VIEW_SELF,
                                                *scoping.OPERATOR_BOOKING_PERMISSIONS)]

    def get_queryset(self):
        return scoping.bookings_detailed(_actor(self.request))


class _BookingAction(APIView):
    """A write on one booking, scoped so a foreign id is a 404."""

    def scope(self, request):
        return scoping.bookings_for(_actor(request))

    def respond(self, request, booking, code=status.HTTP_200_OK):
        return Response(_detail(_actor(request), booking.pk), status=code)


@extend_schema(request=s.OutcomeSerializer, responses=s.BookingDetailSerializer)
class BookingReviewView(_BookingAction):
    """UC-VH-003: forward or reject."""

    permission_classes = [MODULE, HasPermission(perms.BOOKING_REVIEW)]

    def post(self, request, pk):
        p = s.OutcomeSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        booking = booking_service.review(booking_id=pk, actor=_actor(request),
                                         scope=self.scope(request), **p.validated_data)
        return self.respond(request, booking)


@extend_schema(request=s.OutcomeSerializer, responses=s.BookingDetailSerializer)
class BookingDecisionView(_BookingAction):
    """UC-VH-004: approve or reject a forwarded booking."""

    permission_classes = [MODULE, HasPermission(perms.BOOKING_APPROVE)]

    def post(self, request, pk):
        p = s.OutcomeSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        booking = booking_service.decide(booking_id=pk, actor=_actor(request),
                                         scope=self.scope(request), **p.validated_data)
        return self.respond(request, booking)


@extend_schema(responses=s.RoomSerializer(many=True))
class BookingAvailabilityView(_BookingAction):
    """AFR-VH-015: free rooms for this booking's dates, same for offline (BR-VH-004)."""

    permission_classes = [MODULE, HasPermission(perms.BOOKING_REVIEW, perms.ROOM_MANAGE)]

    def get(self, request, pk):
        booking = self.scope(request).filter(pk=pk).first()
        if booking is None:
            raise NotFoundError("No such booking.")
        rooms = room_selectors.available_rooms(booking.arrival_date,
                                               booking.departure_date,
                                               exclude_booking_id=booking.pk)
        return Response(s.RoomSerializer(rooms, many=True).data)


@extend_schema(request=s.AllotSerializer, responses=s.BookingDetailSerializer)
class BookingAllotView(_BookingAction):
    """UC-VH-008."""

    permission_classes = [MODULE, HasPermission(perms.ROOM_MANAGE)]

    def post(self, request, pk):
        p = s.AllotSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        booking = booking_service.allot_rooms(booking_id=pk, actor=_actor(request),
                                              rooms=p.validated_data["rooms"],
                                              scope=self.scope(request))
        return self.respond(request, booking)


@extend_schema(request=s.StayTimeSerializer, responses=s.BookingDetailSerializer)
class BookingCheckInView(_BookingAction):
    """UC-VH-009."""

    permission_classes = [MODULE, HasPermission(perms.STAY_UPDATE)]

    def post(self, request, pk):
        p = s.StayTimeSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        booking = booking_service.check_in(booking_id=pk, actor=_actor(request),
                                           at=p.validated_data["at"],
                                           scope=self.scope(request))
        return self.respond(request, booking)


@extend_schema(request=s.StayTimeSerializer, responses=s.BookingDetailSerializer)
class BookingCheckOutView(_BookingAction):
    """UC-VH-021."""

    permission_classes = [MODULE, HasPermission(perms.STAY_UPDATE)]

    def post(self, request, pk):
        p = s.StayTimeSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        booking = booking_service.check_out(booking_id=pk, actor=_actor(request),
                                            at=p.validated_data["at"],
                                            scope=self.scope(request))
        return self.respond(request, booking)


@extend_schema(request=s.ReasonSerializer, responses=s.CancellationSerializer)
class CancellationRequestView(_BookingAction):
    """UC-VH-007: the Indenter asks; the charge case is recorded."""

    permission_classes = [MODULE, HasPermission(perms.CANCELLATION_CREATE)]

    def post(self, request, pk):
        p = s.ReasonSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        row = booking_service.request_cancellation(
            booking_id=pk, actor=_actor(request), scope=self.scope(request),
            **p.validated_data)
        return Response(s.CancellationSerializer(row).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.BookingDetailSerializer)
class CancellationConfirmView(_BookingAction):
    """UC-VH-020."""

    permission_classes = [MODULE, HasPermission(perms.CANCELLATION_APPROVE)]

    def post(self, request, pk):
        booking = booking_service.confirm_cancellation(
            booking_id=pk, actor=_actor(request), scope=self.scope(request))
        return self.respond(request, booking)


@extend_schema(request=s.ModificationWriteSerializer, responses=s.ModificationSerializer)
class ModificationRequestView(_BookingAction):
    """UC-VH-006."""

    permission_classes = [MODULE, HasPermission(perms.MODIFICATION_CREATE)]

    def post(self, request, pk):
        p = s.ModificationWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        data = dict(p.validated_data)
        reason = data.pop("reason", "")
        row = booking_service.request_modification(
            booking_id=pk, actor=_actor(request), changes=data, reason=reason,
            scope=self.scope(request))
        return Response(s.ModificationSerializer(row).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.ModificationSerializer)
class ModificationConfirmView(APIView):
    """UC-VH-022 (provisional): reachable only once the institute names who
    holds visitor_hostel.modification.approve."""

    permission_classes = [MODULE, HasPermission(perms.MODIFICATION_APPROVE)]

    def post(self, request, pk):
        row = booking_service.confirm_modification(modification_id=pk,
                                                   actor=_actor(request))
        return Response(s.ModificationSerializer(row).data)


@extend_schema(responses=s.ModificationSerializer(many=True))
class ModificationListView(generics.ListAPIView):
    serializer_class = s.ModificationSerializer
    permission_classes = [MODULE, HasPermission(perms.MODIFICATION_APPROVE, perms.BOOKING_VIEW)]

    def get_queryset(self):
        return ModificationRequest.objects.filter(status="requested").order_by("-id")


# -- Meals and bills -------------------------------------------------------------
@extend_schema(request=s.MealWriteSerializer, responses=s.MealSerializer)
class BookingMealsView(_BookingAction):
    """UC-VH-012."""

    permission_classes = [MODULE, HasPermission(perms.MEAL_MANAGE)]

    def post(self, request, pk):
        p = s.MealWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        meal = billing_service.add_meal(booking_id=pk, actor=_actor(request),
                                        scope=self.scope(request), **p.validated_data)
        return Response(s.MealSerializer(meal).data, status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.BillSerializer)
class BookingBillView(_BookingAction):
    """UC-VH-013: generate."""

    permission_classes = [MODULE, HasPermission(perms.BILL_MANAGE)]

    def post(self, request, pk):
        bill = billing_service.generate(booking_id=pk, actor=_actor(request),
                                        scope=self.scope(request))
        return Response(s.BillSerializer(bill).data, status=status.HTTP_201_CREATED)


@extend_schema(responses=s.BillSerializer(many=True))
class BillListView(generics.ListAPIView):
    serializer_class = s.BillSerializer
    permission_classes = [MODULE, HasPermission(perms.BILL_MANAGE, perms.BILL_VIEW)]

    def get_queryset(self):
        qs = scoping.bills_for(_actor(self.request))
        state = self.request.query_params.get("status")
        if state in ("generated", "settled"):
            qs = qs.filter(status=state)
        return qs.order_by("-id")


@extend_schema(request=s.SettleSerializer, responses=s.BillSerializer)
class BillSettleView(APIView):
    """BR-VH-036."""

    permission_classes = [MODULE, HasPermission(perms.BILL_MANAGE)]

    def post(self, request, pk):
        p = s.SettleSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        bill = billing_service.settle(bill_id=pk, actor=_actor(request),
                                      scope=scoping.bills_for(_actor(request)),
                                      **p.validated_data)
        return Response(s.BillSerializer(bill).data)


@extend_schema(request=s.VerifySerializer, responses=s.BillSerializer)
class BillVerifyView(APIView):
    """AFR-VH-065."""

    permission_classes = [MODULE, HasPermission(perms.BILL_MANAGE)]

    def post(self, request, pk):
        p = s.VerifySerializer(data=request.data)
        p.is_valid(raise_exception=True)
        bill = billing_service.record_verification(
            bill_id=pk, actor=_actor(request), scope=scoping.bills_for(_actor(request)),
            **p.validated_data)
        return Response(s.BillSerializer(bill).data)


# -- Rooms, tariffs, duty --------------------------------------------------------
@extend_schema(request=s.RoomWriteSerializer, responses=s.RoomSerializer)
class RoomListView(generics.ListCreateAPIView):
    serializer_class = s.RoomSerializer
    permission_classes = [MODULE, HasPermission(perms.ROOM_MANAGE, perms.BOOKING_APPROVE)]

    def get_queryset(self):
        return Room.objects.order_by("number")

    def create(self, request, *args, **kwargs):
        p = s.RoomWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        room = config_service.create_room(actor=_actor(request), **p.validated_data)
        return Response(s.RoomSerializer(room).data, status=status.HTTP_201_CREATED)


@extend_schema(request=s.RoomActiveSerializer, responses=s.RoomSerializer)
class RoomActiveView(APIView):
    permission_classes = [MODULE, HasPermission(perms.ROOM_MANAGE)]

    def post(self, request, pk):
        p = s.RoomActiveSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        room = config_service.set_room_active(room_id=pk, actor=_actor(request),
                                              **p.validated_data)
        return Response(s.RoomSerializer(room).data)


class TariffListView(APIView):
    """GET for both offices; POST needs the unassigned tariff authority (UC-VH-011)."""

    def get_permissions(self):
        code = perms.TARIFF_MANAGE if self.request.method == "POST" else perms.TARIFF_VIEW
        return [MODULE(), HasPermission(code)()]

    @extend_schema(responses=s.TariffsSerializer)
    def get(self, request):
        return Response({
            "room": s.RoomTariffSerializer(
                RoomTariff.objects.order_by("category", "occupancy", "-effective_from"),
                many=True).data,
            "meal": s.MealTariffSerializer(
                MealTariff.objects.order_by("item", "-effective_from"), many=True).data,
        })

    @extend_schema(request=s.TariffWriteSerializer, responses=s.RoomTariffSerializer)
    def post(self, request):
        p = s.TariffWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        d = p.validated_data
        if d["kind"] == "room":
            row = config_service.add_room_tariff(
                category=d["category"], occupancy=d["occupancy"], rate=d["rate"],
                effective_from=d["effective_from"], actor=_actor(request))
            data = s.RoomTariffSerializer(row).data
        else:
            row = config_service.add_meal_tariff(
                item=d["item"], rate=d["rate"], effective_from=d["effective_from"],
                actor=_actor(request))
            data = s.MealTariffSerializer(row).data
        return Response(data, status=status.HTTP_201_CREATED)


@extend_schema(responses=s.DutySerializer(many=True))
class DutyView(generics.ListAPIView):
    serializer_class = s.DutySerializer
    permission_classes = [MODULE, HasPermission(perms.DUTY_VIEW)]
    pagination_class = None

    def get_queryset(self):
        return DutyAssignment.objects.filter(role__in=duty.ROLES,
                                             ended_at__isnull=True).order_by("role")


# -- Inventory -------------------------------------------------------------------
@extend_schema(request=s.InventoryWriteSerializer, responses=s.InventoryItemSerializer)
class InventoryListView(generics.ListCreateAPIView):
    serializer_class = s.InventoryItemSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission(perms.INVENTORY_MANAGE)()]
        return [MODULE(), HasPermission(perms.INVENTORY_MANAGE, perms.INVENTORY_VIEW)()]

    def get_queryset(self):
        qs = scoping.inventory_for(_actor(self.request)).order_by("name")
        if self.request.query_params.get("below_threshold") == "true":
            qs = qs.filter(quantity__lt=F("min_threshold"))
        return qs

    def create(self, request, *args, **kwargs):
        p = s.InventoryWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        item = inventory_service.create_item(actor=_actor(request), **p.validated_data)
        return Response(s.InventoryItemSerializer(item).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=s.AdjustSerializer, responses=s.InventoryItemSerializer)
class InventoryAdjustView(APIView):
    permission_classes = [MODULE, HasPermission(perms.INVENTORY_MANAGE)]

    def post(self, request, pk):
        p = s.AdjustSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        item = inventory_service.adjust(item_id=pk, actor=_actor(request),
                                        **p.validated_data)
        return Response(s.InventoryItemSerializer(item).data)


@extend_schema(request=s.ThresholdSerializer, responses=s.InventoryItemSerializer)
class InventoryThresholdView(APIView):
    permission_classes = [MODULE, HasPermission(perms.INVENTORY_MANAGE)]

    def post(self, request, pk):
        p = s.ThresholdSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        item = inventory_service.set_threshold(item_id=pk, actor=_actor(request),
                                               **p.validated_data)
        return Response(s.InventoryItemSerializer(item).data)


@extend_schema(request=s.ReplenishmentWriteSerializer, responses=s.ReplenishmentSerializer)
class ReplenishmentListView(generics.ListCreateAPIView):
    serializer_class = s.ReplenishmentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission(perms.REPLENISHMENT_CREATE)()]
        return [MODULE(), HasPermission(perms.REPLENISHMENT_CREATE, perms.REPLENISHMENT_APPROVE,
                                        perms.INVENTORY_VIEW)()]

    def get_queryset(self):
        qs = scoping.replenishments_for(_actor(self.request))
        state = self.request.query_params.get("status")
        if state in ("pending", "approved"):
            qs = qs.filter(status=state)
        return qs.order_by("-id")

    def create(self, request, *args, **kwargs):
        p = s.ReplenishmentWriteSerializer(data=request.data)
        p.is_valid(raise_exception=True)
        row = inventory_service.raise_replenishment(actor=_actor(request),
                                                    **p.validated_data)
        return Response(s.ReplenishmentSerializer(row).data,
                        status=status.HTTP_201_CREATED)


@extend_schema(request=None, responses=s.ReplenishmentSerializer)
class ReplenishmentApproveView(APIView):
    """UC-VH-015."""

    permission_classes = [MODULE, HasPermission(perms.REPLENISHMENT_APPROVE)]

    def post(self, request, pk):
        row = inventory_service.approve_replenishment(requirement_id=pk,
                                                      actor=_actor(request))
        return Response(s.ReplenishmentSerializer(row).data)


# -- Alerts and reports ----------------------------------------------------------
@extend_schema(responses=s.StayAlertSerializer(many=True))
class StayAlertListView(generics.ListAPIView):
    serializer_class = s.StayAlertSerializer
    permission_classes = [MODULE, HasPermission(perms.ALERT_VIEW)]

    def get_queryset(self):
        qs = scoping.stay_alerts_for(_actor(self.request))
        kind = self.request.query_params.get("kind")
        if kind in ("no_show", "overstay"):
            qs = qs.filter(kind=kind)
        return qs.order_by("-id")


_INCHARGE_REPORTS = {
    "booking-summary": reports.booking_summary,
    "category-occupancy": reports.category_occupancy,
    "revenue": reports.revenue_summary,
    "inventory-usage": reports.inventory_usage,
}


@extend_schema(parameters=[OpenApiParameter("from", str), OpenApiParameter("to", str)],
               responses=dict)
class InChargeReportView(APIView):
    """UC-VH-017: booking summary, category occupancy, revenue, inventory usage."""

    permission_classes = [MODULE, HasPermission(perms.REPORT_VIEW)]

    def get(self, request, kind):
        fn = _INCHARGE_REPORTS.get(kind)
        if fn is None:
            raise NotFoundError("No such report.")
        start, end = _range(request)
        return Response(fn(start, end))


@extend_schema(parameters=[OpenApiParameter("date", str), OpenApiParameter("from", str),
                           OpenApiParameter("to", str)],
               responses=dict)
class OperationsReportView(APIView):
    """UC-VH-018: daily occupancy, arrivals/departures, pending approvals,
    no-show and overstay log."""

    permission_classes = [MODULE, HasPermission(perms.OPERATIONS_REPORT_VIEW)]

    def get(self, request, kind):
        params, today = request.query_params, timezone.localdate()
        if kind == "daily-occupancy":
            return Response(reports.daily_occupancy(_date_param(params, "date", today)))
        if kind == "arrivals-departures":
            return Response(reports.arrivals_and_departures(
                _date_param(params, "from", today)))
        if kind == "pending-approvals":
            return Response(reports.pending_approvals())
        if kind == "no-show-overstay":
            start, end = _range(request)
            return Response(reports.no_show_overstay_log(start, end))
        raise NotFoundError("No such report.")
