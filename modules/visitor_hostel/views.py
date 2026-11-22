"""Hostel API: IAM authorization, scoped reads, validated transactional commands."""

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from . import services
from .models import (
    AuditEvent,
    Bill,
    BookingRequest,
    InventoryItem,
    InventoryReplenishment,
    Room,
    VisitorCategoryTariff,
)
from .permissions import HostelPermission, is_operator
from .serializers import (
    AllotmentInputSerializer,
    AuditEventSerializer,
    BillSerializer,
    BookingRequestSerializer,
    DecisionSerializer,
    HostelReportSerializer,
    InventoryItemSerializer,
    InventoryReplenishmentSerializer,
    MealBookingSerializer,
    ReasonSerializer,
    RoomSerializer,
    RouteSerializer,
    SettlementSerializer,
    StatusSerializer,
    VisitorCategoryTariffSerializer,
)


def bookings_for(principal):
    qs = BookingRequest.objects.all()
    if not is_operator(principal):
        qs = qs.filter(indenter_id=principal.user_id)
    return qs


class BookingListCreateView(generics.ListCreateAPIView):
    queryset = BookingRequest.objects.none()
    serializer_class = BookingRequestSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.request"

    def get_queryset(self):
        return (
            bookings_for(self.request.principal)
            .select_related("bill")
            .prefetch_related("allotments__room", "meal_bookings")
            .order_by("-created_at", "-pk")
        )

    @transaction.atomic
    def perform_create(self, serializer):
        booking = serializer.save(
            indenter_id=self.request.principal.user_id, is_offline=False, status="pending"
        )
        services.audit(booking, self.request.principal, "submitted")


class OfflineBookingCreateView(generics.CreateAPIView):
    serializer_class = BookingRequestSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.manage"

    @transaction.atomic
    def perform_create(self, serializer):
        booking = serializer.save(indenter_id=None, is_offline=True, status="pending")
        services.audit(booking, self.request.principal, "offline_submitted")


class BookingDetailView(generics.RetrieveUpdateAPIView):
    queryset = BookingRequest.objects.none()
    serializer_class = BookingRequestSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.request"

    def get_queryset(self):
        return (
            bookings_for(self.request.principal)
            .select_related("bill")
            .prefetch_related("allotments__room", "meal_bookings")
        )

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        booking = get_object_or_404(
            bookings_for(request.principal).select_for_update(), pk=kwargs["pk"]
        )
        services.require_state(booking, "pending")
        services.before_arrival(booking)
        serializer = self.get_serializer(
            booking, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        services.audit(booking, request.principal, "edited", fields=list(serializer.validated_data))
        return Response(serializer.data)


@extend_schema(responses=StatusSerializer)
class BookingCommand(generics.GenericAPIView):
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.manage"
    serializer_class = ReasonSerializer

    def booking(self, request, pk):
        return get_object_or_404(bookings_for(request.principal).select_for_update(), pk=pk)

    def inputs(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data


class CaretakerRouteBookingView(BookingCommand):
    serializer_class = RouteSerializer

    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        services.require_state(booking, "pending")
        if data["action"] == "forward":
            if services.available_rooms(booking).count() < booking.number_of_rooms:
                raise ValidationError("Insufficient room availability.")
            booking.status = "forwarded"
        else:
            booking.status = "rejected"
            booking.rejection_reason = data["reason"]
        booking.save()
        services.audit(booking, request.principal, booking.status, reason=data["reason"])
        return Response({"status": booking.status})


class InChargeApproveBookingView(BookingCommand):
    permission_code = "visitor_hostel.booking.approve"
    serializer_class = DecisionSerializer

    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        services.require_state(booking, "forwarded")
        booking.status = "approved" if data["decision"] == "approve" else "rejected"
        booking.rejection_reason = data["reason"] if booking.status == "rejected" else ""
        booking.save()
        services.audit(booking, request.principal, booking.status, reason=data["reason"])
        return Response({"status": booking.status})


class RoomAllotmentView(BookingCommand):
    serializer_class = AllotmentInputSerializer

    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        services.allot(booking, data["room_ids"])
        services.audit(booking, request.principal, "allotted", room_ids=data["room_ids"])
        return Response({"status": booking.status})


class CheckInView(BookingCommand):
    @extend_schema(request=None, responses=BookingRequestSerializer)
    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        services.require_state(booking, "confirmed")
        allotments = list(booking.allotments.all())
        if len(allotments) != booking.number_of_rooms:
            raise ValidationError("All requested rooms must be allotted before check-in.")
        room_ids = [a.room_id for a in allotments]
        rooms = list(Room.objects.select_for_update().filter(pk__in=room_ids).order_by("pk"))
        if any(r.status != "available" for r in rooms):
            raise ValidationError("An allotted room is occupied or under maintenance.")
        if not services.arrival(booking) <= timezone.now() < services.departure(booking):
            raise ValidationError("Check-in must occur within the approved stay.")
        booking.status = "checked_in"
        booking.save()
        booking.allotments.update(actual_check_in=timezone.now())
        Room.objects.filter(pk__in=room_ids).update(status="occupied")
        services.audit(booking, request.principal, "checked_in")
        return Response(BookingRequestSerializer(booking).data)


class CheckOutAndBillView(BookingCommand):
    @extend_schema(request=None, responses=BillSerializer)
    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        if booking.status == "checked_out":
            return Response(BillSerializer(booking.bill).data)
        services.require_state(booking, "checked_in")
        bill = services.create_bill(booking)
        booking.status = "checked_out"
        booking.save()
        booking.allotments.update(actual_check_out=timezone.now())
        Room.objects.filter(pk__in=booking.allotments.values("room_id")).update(status="available")
        services.audit(booking, request.principal, "checked_out", bill_id=bill.pk)
        return Response(BillSerializer(bill).data)


class BookingCancellationView(BookingCommand):
    permission_code = "visitor_hostel.booking.request"

    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        services.require_state(booking, "pending", "forwarded", "approved", "confirmed")
        services.before_arrival(booking)
        if booking.cancellation_requested_at is None:
            booking.cancellation_requested_at = timezone.now()
            booking.cancellation_reason = data["reason"]
            booking.save()
            services.audit(booking, request.principal, "cancellation_requested", **data)
        return Response({"status": "pending_cancellation_review"})


class ConfirmCancellationView(BookingCommand):
    @extend_schema(request=None, responses=BillSerializer)
    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        if booking.status == "cancelled":
            return Response(BillSerializer(booking.bill).data)
        services.require_state(booking, "pending", "forwarded", "approved", "confirmed")
        if booking.cancellation_requested_at is None:
            raise ValidationError("No cancellation request is pending.")
        bill = services.create_bill(
            booking,
            cancellation=services.cancellation_charge(booking, booking.cancellation_requested_at),
        )
        booking.status = "cancelled"
        booking.save()
        services.audit(booking, request.principal, "cancelled", bill_id=bill.pk)
        return Response(BillSerializer(bill).data)


@extend_schema(responses={201: MealBookingSerializer})
class MealBookingView(BookingCommand):
    serializer_class = MealBookingSerializer

    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        services.require_state(booking, "checked_in")
        data = self.inputs(request)
        if not booking.check_in_date <= data["date"] <= booking.check_out_date:
            raise ValidationError("Meal date must be within the approved stay.")
        meal = booking.meal_bookings.create(**data)
        services.audit(booking, request.principal, "meal_recorded", meal_id=meal.pk)
        return Response(self.get_serializer(meal).data, status=201)


class SettlementView(BookingCommand):
    serializer_class = SettlementSerializer

    @extend_schema(responses=BillSerializer)
    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        bill = get_object_or_404(Bill, booking=booking)
        if bill.is_settled_offline:
            raise ValidationError("Settlement has already been recorded.")
        bill.is_settled_offline = True
        bill.settlement_date = timezone.now()
        bill.remarks = data["receipt_number"]
        bill.save(update_fields=["is_settled_offline", "settlement_date", "remarks", "updated_at"])
        services.audit(booking, request.principal, "cash_settlement", **data)
        return Response(BillSerializer(bill).data)


class InventoryListView(generics.ListCreateAPIView):
    queryset = InventoryItem.objects.order_by("pk")
    serializer_class = InventoryItemSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.inventory.manage"

    @transaction.atomic
    def perform_create(self, serializer):
        item = serializer.save()
        services.inventory_alert(item)
        services.audit(None, self.request.principal, "inventory_created", item_id=item.pk)


class InventoryReplenishView(generics.ListCreateAPIView):
    queryset = InventoryReplenishment.objects.select_related("item").order_by("pk")
    serializer_class = InventoryReplenishmentSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.inventory.manage"


@extend_schema(responses=InventoryReplenishmentSerializer)
class InventoryDecisionView(generics.GenericAPIView):
    serializer_class = DecisionSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.inventory.approve"

    @transaction.atomic
    def post(self, request, pk):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        entry = get_object_or_404(InventoryReplenishment.objects.select_for_update(), pk=pk)
        if entry.status != "pending":
            raise ValidationError("This requirement has already been decided.")
        entry.status = (
            "approved" if serializer.validated_data["decision"] == "approve" else "rejected"
        )
        entry.remarks = serializer.validated_data["reason"]
        entry.save()
        services.audit(
            None,
            request.principal,
            "replenishment_decided",
            replenishment_id=entry.pk,
            status=entry.status,
        )
        return Response(InventoryReplenishmentSerializer(entry).data)


class TariffListCreateView(generics.ListCreateAPIView):
    queryset = VisitorCategoryTariff.objects.order_by("-effective_from", "-pk")
    serializer_class = VisitorCategoryTariffSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.tariff.manage"


class InventoryDetailView(generics.RetrieveUpdateAPIView):
    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.inventory.manage"

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        item = get_object_or_404(InventoryItem.objects.select_for_update(), pk=kwargs["pk"])
        serializer = self.get_serializer(
            item, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        old_quantity = item.quantity
        item = serializer.save()
        services.inventory_alert(item)
        services.audit(
            None,
            request.principal,
            "inventory_updated",
            item_id=item.pk,
            previous_quantity=old_quantity,
            quantity=item.quantity,
        )
        return Response(serializer.data)


class ModificationRequestView(BookingCommand):
    permission_code = "visitor_hostel.booking.request"
    serializer_class = BookingRequestSerializer

    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        services.require_state(booking, "approved", "confirmed")
        services.before_arrival(booking)
        if booking.cancellation_requested_at:
            raise ValidationError("Cancellation review is pending.")
        serializer = self.get_serializer(booking, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        # Store only validated writable fields, encoded with the response serializer.
        import json

        from rest_framework.renderers import JSONRenderer

        booking.modification_request = json.loads(JSONRenderer().render(serializer.validated_data))
        if not booking.modification_request:
            raise ValidationError("No booking changes supplied.")
        booking.save()
        services.audit(booking, request.principal, "modification_requested")
        return Response({"status": "pending_modification_review"})


@extend_schema(responses=BookingRequestSerializer)
class ModificationDecisionView(BookingCommand):
    serializer_class = DecisionSerializer

    @transaction.atomic
    def post(self, request, pk):
        data = self.inputs(request)
        booking = self.booking(request, pk)
        services.require_state(booking, "approved", "confirmed")
        services.before_arrival(booking)
        if not booking.modification_request:
            raise ValidationError("No modification is pending.")
        if data["decision"] == "approve":
            serializer = BookingRequestSerializer(
                booking, data=booking.modification_request, partial=True
            )
            serializer.is_valid(raise_exception=True)
            # Release reservation and repeat approval/allotment for changed stay details.
            booking.allotments.all().delete()
            serializer.save(status="pending")
        changes = booking.modification_request
        booking.modification_request = {}
        booking.save()
        services.audit(booking, request.principal, "modification_decided", changes=changes, **data)
        return Response(BookingRequestSerializer(booking).data)


class NoShowView(BookingCommand):
    @extend_schema(request=None, responses=BillSerializer)
    @transaction.atomic
    def post(self, request, pk):
        booking = self.booking(request, pk)
        services.require_state(booking, "confirmed")
        if timezone.now() < services.arrival(booking):
            raise ValidationError("The guest is not yet due to arrive.")
        from decimal import Decimal

        charge = services.money(
            services.tariff_for(booking) * booking.number_of_rooms * Decimal("0.5")
        )
        bill = services.create_bill(booking, cancellation=charge)
        booking.status = "cancelled"
        booking.save()
        services.audit(booking, request.principal, "no_show", bill_id=bill.pk)
        return Response(BillSerializer(bill).data)


@extend_schema(responses=AuditEventSerializer(many=True))
class BookingHistoryView(generics.GenericAPIView):
    queryset = BookingRequest.objects.none()
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.request"
    serializer_class = BookingRequestSerializer

    def get(self, request, pk):
        booking = get_object_or_404(bookings_for(request.principal), pk=pk)
        return Response(
            list(
                booking.audit_events.order_by("pk").values(
                    "action", "actor_id", "created_at", "details"
                )
            )
        )


@extend_schema(responses=HostelReportSerializer)
class HostelReportsView(generics.GenericAPIView):
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.request"
    serializer_class = BookingRequestSerializer

    def get(self, request):
        if not is_operator(request.principal):
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Operational reports require a current hostel appointment.")
        from django.db.models import Count, Sum

        from .models import Notification

        today = timezone.localdate()
        bookings = BookingRequest.objects.all()
        return Response(
            {
                "booking_summary": list(bookings.values("status").annotate(count=Count("id"))),
                "category_occupancy": list(
                    bookings.filter(status="checked_in")
                    .values("visitor_category")
                    .annotate(rooms=Sum("number_of_rooms"), occupants=Sum("number_of_occupants"))
                ),
                "billing_summary": Bill.objects.aggregate(total=Sum("total_amount")),
                "inventory_usage": list(
                    AuditEvent.objects.filter(action="inventory_updated")
                    .order_by("-pk")
                    .values("details", "created_at")[:100]
                ),
                "daily_occupancy": list(
                    bookings.filter(status="checked_in").values(
                        "id", "visitor_name", "number_of_rooms"
                    )
                ),
                "arrivals": list(
                    bookings.filter(check_in_date=today, status="confirmed").values(
                        "id", "visitor_name"
                    )
                ),
                "departures": list(
                    bookings.filter(check_out_date=today, status="checked_in").values(
                        "id", "visitor_name"
                    )
                ),
                "pending_approvals": bookings.filter(status__in=["pending", "forwarded"]).count(),
                "alerts": list(
                    Notification.objects.filter(
                        event__in=["no_show_alert", "overstay_alert", "inventory_threshold"]
                    )
                    .order_by("-pk")
                    .values("event", "booking_id", "created_at")[:100]
                ),
            }
        )


class RoomListCreateView(generics.ListCreateAPIView):
    queryset = Room.objects.order_by("room_number")
    serializer_class = RoomSerializer
    permission_classes = [HostelPermission]
    permission_code = "visitor_hostel.booking.manage"

    def get_queryset(self):
        rooms = super().get_queryset()
        booking_id = self.request.query_params.get("booking")
        if booking_id is not None:
            if not booking_id.isdecimal():
                raise ValidationError({"booking": "A positive booking id is required."})
            booking = get_object_or_404(BookingRequest, pk=booking_id)
            rooms = services.available_rooms(booking).order_by("room_number")
        return rooms

    @transaction.atomic
    def perform_create(self, serializer):
        room = serializer.save(status="available")
        services.audit(None, self.request.principal, "room_created", room_id=room.pk)
