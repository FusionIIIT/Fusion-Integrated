"""API views for Visitors Hostel (VH) module."""
from decimal import Decimal

from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.vh.api.serializers import (
    BillSerializer,
    BookingActionSerializer,
    BookingSerializer,
    InventoryItemSerializer,
    InventoryReplenishmentSerializer,
    MealBookingSerializer,
    RoomSerializer,
    TariffSerializer,
    VisitorCategorySerializer,
)
from modules.vh.models import (
    Bill,
    Booking,
    BookingStatus,
    InventoryItem,
    InventoryReplenishment,
    MealBooking,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    Tariff,
    VisitorCategory,
)


class VisitorCategoryViewSet(viewsets.ModelViewSet):
    """View and manage visitor categories (CFR-VH-009)."""

    queryset = VisitorCategory.objects.all()
    serializer_class = VisitorCategorySerializer
    permission_classes = [permissions.AllowAny]


class RoomViewSet(viewsets.ModelViewSet):
    """View and manage hostel rooms (CFR-VH-007)."""

    queryset = Room.objects.all()
    serializer_class = RoomSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        status_param = self.request.query_params.get("status")
        room_type = self.request.query_params.get("room_type")
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if room_type:
            qs = qs.filter(room_type=room_type.upper())
        return qs


class TariffViewSet(viewsets.ModelViewSet):
    """View and manage tariff structure (CFR-VH-009)."""

    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer
    permission_classes = [permissions.AllowAny]


class BookingViewSet(viewsets.ModelViewSet):
    """Lifecycle and management of visitor hostel bookings.

    Covers Indenter submissions (CFR-VH-002), Caretaker review/offline booking
    (CFR-VH-003, CFR-VH-004), In-Charge approvals, cancellations (CFR-VH-006),
    room allotment, and check-in/out stay progression (BW-VH-10).
    """

    queryset = (
        Booking.objects.select_related("visitor_category")
        .prefetch_related("allotments", "meal_bookings")
        .all()
    )
    serializer_class = BookingSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = super().get_queryset()
        indenter_id = self.request.query_params.get("indenter_id")
        status_param = self.request.query_params.get("status")
        is_offline = self.request.query_params.get("is_offline")

        if indenter_id:
            qs = qs.filter(indenter_id=indenter_id)
        if status_param:
            qs = qs.filter(status=status_param.upper())
        if is_offline is not None:
            qs = qs.filter(is_offline=is_offline.lower() in ("true", "1"))
        return qs

    def perform_create(self, serializer):
        user_id = getattr(self.request.user, "id", None) or serializer.validated_data.get(
            "indenter_id", 1
        )
        serializer.save(indenter_id=user_id, status=BookingStatus.PENDING)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def forward(self, request, pk=None):
        """Caretaker forwards booking to VH In-Charge for decision (BW-VH-02, BW-VH-03)."""
        booking = self.get_object()
        if booking.status != BookingStatus.PENDING:
            return Response(
                {"error": f"Cannot forward booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        booking.caretaker_remarks = action_ser.validated_data.get("remarks", "")
        booking.status = BookingStatus.FORWARDED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def approve(self, request, pk=None):
        """VH In-Charge approves booking (CW-VH-01, AFR-VH-018)."""
        booking = self.get_object()
        if booking.status not in (BookingStatus.PENDING, BookingStatus.FORWARDED):
            return Response(
                {"error": f"Cannot approve booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        booking.incharge_remarks = action_ser.validated_data.get("remarks", "")
        booking.status = BookingStatus.APPROVED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def reject(self, request, pk=None):
        """Caretaker or In-Charge rejects booking (BW-VH-01, BW-VH-03, BW-VH-04, BW-VH-06)."""
        booking = self.get_object()
        terminal_statuses = (
            BookingStatus.CHECKED_IN,
            BookingStatus.CHECKED_OUT,
            BookingStatus.CANCELLED,
        )
        if booking.status in terminal_statuses:
            return Response(
                {"error": f"Cannot reject booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        remarks = action_ser.validated_data.get("remarks", "")
        if booking.status == BookingStatus.FORWARDED:
            booking.incharge_remarks = remarks
        else:
            booking.caretaker_remarks = remarks
        booking.status = BookingStatus.REJECTED
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def allot_room(self, request, pk=None):
        """Allot room(s) to approved booking (BR-VH-012, BW-VH-10)."""
        booking = self.get_object()
        if booking.status not in (BookingStatus.APPROVED, BookingStatus.ROOM_ALLOTTED):
            return Response(
                {"error": "Rooms can only be allotted after booking approval (BR-VH-012)."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        room_ids = action_ser.validated_data.get("room_ids", [])
        if not room_ids:
            return Response(
                {"error": "room_ids list is required for room allotment."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        allotted_rooms = []
        for r_id in room_ids:
            try:
                room = Room.objects.get(id=r_id)
            except Room.DoesNotExist:
                return Response(
                    {"error": f"Room with ID {r_id} does not exist."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if room.status != RoomStatus.AVAILABLE:
                return Response(
                    {"error": f"Room {room.room_number} is not available (status: {room.status})."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            RoomAllotment.objects.get_or_create(booking=booking, room=room)
            room.status = RoomStatus.OCCUPIED
            room.save()
            allotted_rooms.append(room.room_number)

        booking.status = BookingStatus.ROOM_ALLOTTED
        booking.save()
        return Response({
            "message": f"Allotted room(s): {', '.join(allotted_rooms)}",
            "booking": BookingSerializer(booking).data,
        })

    @action(detail=True, methods=["post"])
    def check_in(self, request, pk=None):
        """Record guest check-in (BW-VH-10, AFR-VH-041)."""
        booking = self.get_object()
        if booking.status != BookingStatus.ROOM_ALLOTTED:
            return Response(
                {"error": "Guest can only check in after room allotment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        booking.allotments.update(check_in_time=now)
        booking.status = BookingStatus.CHECKED_IN
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def check_out(self, request, pk=None):
        """Record guest check-out and generate bill (BW-VH-10, AFR-VH-042, CFR-VH-011)."""
        booking = self.get_object()
        if booking.status != BookingStatus.CHECKED_IN:
            return Response(
                {"error": "Guest must be checked in before checking out."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        booking.allotments.update(check_out_time=now)

        # Free all allotted rooms
        for allotment in booking.allotments.all():
            allotment.room.status = RoomStatus.AVAILABLE
            allotment.room.save()

        # Calculate stay duration
        days = max((booking.check_out_date - booking.check_in_date).days, 1)

        # Find tariff or use fallback
        tariff = Tariff.objects.filter(
            category=booking.visitor_category
        ).order_by("-effective_from").first()
        rate_per_day = tariff.rate_per_day if tariff else Decimal("500.00")
        room_charges = rate_per_day * Decimal(str(days)) * Decimal(str(booking.number_of_rooms))

        # Calculate meal charges
        meal_charges = sum(
            (m.total_amount for m in booking.meal_bookings.all()),
            Decimal("0.00"),
        )
        total_amount = room_charges + meal_charges

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.room_charges = room_charges
        bill.meal_charges = meal_charges
        bill.total_amount = total_amount
        bill.save()

        booking.status = BookingStatus.CHECKED_OUT
        booking.save()
        return Response({
            "message": "Guest checked out successfully and bill generated.",
            "booking": BookingSerializer(booking).data,
            "bill": BillSerializer(bill).data,
        })

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def cancel(self, request, pk=None):
        """Cancel booking with applicable charges schedule (BR-VH-006..009, CW-VH-02).

        Schedule:
          - >= 7 days before arrival: 0% charge
          - Within 7 days before arrival: 25% of one-day room rent
          - Same day or after: 50% of one-day room rent
        """
        booking = self.get_object()
        terminal_statuses = (
            BookingStatus.CHECKED_IN,
            BookingStatus.CHECKED_OUT,
            BookingStatus.CANCELLED,
        )
        if booking.status in terminal_statuses:
            return Response(
                {"error": f"Cannot cancel booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        reason = action_ser.validated_data.get("reason", "")

        today = timezone.localdate()
        days_to_arrival = (booking.check_in_date - today).days

        tariff = Tariff.objects.filter(
            category=booking.visitor_category
        ).order_by("-effective_from").first()
        one_day_rent = tariff.rate_per_day if tariff else Decimal("500.00")
        base_rent = one_day_rent * Decimal(str(booking.number_of_rooms))

        if days_to_arrival >= 7:
            cancellation_charge = Decimal("0.00")
        elif days_to_arrival > 0:
            cancellation_charge = (base_rent * Decimal("0.25")).quantize(Decimal("0.01"))
        else:
            cancellation_charge = (base_rent * Decimal("0.50")).quantize(Decimal("0.01"))

        # Release any rooms that were allotted
        for allotment in booking.allotments.all():
            allotment.room.status = RoomStatus.AVAILABLE
            allotment.room.save()

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.cancellation_charges = cancellation_charge
        bill.total_amount = cancellation_charge
        bill.save()

        booking.status = BookingStatus.CANCELLED
        booking.cancellation_reason = reason
        booking.save()

        return Response({
            "message": f"Booking cancelled. Cancellation charge: Rs {cancellation_charge}.",
            "booking": BookingSerializer(booking).data,
            "bill": BillSerializer(bill).data,
        })


class MealBookingViewSet(viewsets.ModelViewSet):
    """Manage meal bookings for residing guests (CFR-VH-010)."""

    queryset = MealBooking.objects.all()
    serializer_class = MealBookingSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        persons = serializer.validated_data.get("number_of_persons", 1)
        rate = serializer.validated_data.get("rate", Decimal("100.00"))
        total = rate * Decimal(str(persons))
        serializer.save(rate=rate, total_amount=total)


class BillViewSet(viewsets.ModelViewSet):
    """View and offline-settle bills (CFR-VH-011)."""

    queryset = Bill.objects.select_related("booking").all()
    serializer_class = BillSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def settle(self, request, pk=None):
        """Settle bill offline in cash and finalize (BR-VH-036, BR-VH-037)."""
        bill = self.get_object()
        notes = request.data.get("guest_verification_notes", "")
        bill.is_settled = True
        bill.settled_at = timezone.now()
        bill.is_finalized = True
        if notes:
            bill.guest_verification_notes = notes
        bill.save()
        return Response(BillSerializer(bill).data)


class InventoryItemViewSet(viewsets.ModelViewSet):
    """Inventory management and threshold alert monitoring (CFR-VH-012)."""

    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"])
    def alerts(self, request):
        """Return items where current quantity is below threshold (BR-VH-041)."""
        items = [i for i in self.get_queryset() if i.is_below_threshold]
        return Response(InventoryItemSerializer(items, many=True).data)

    @action(detail=True, methods=["post"])
    def request_replenishment(self, request, pk=None):
        """Caretaker requests inventory replenishment (CFR-VH-013)."""
        item = self.get_object()
        qty = request.data.get("quantity_requested", 10)
        remarks = request.data.get("remarks", "")
        user_id = getattr(request.user, "id", None) or 1
        rep = InventoryReplenishment.objects.create(
            item=item,
            quantity_requested=qty,
            requested_by_user_id=user_id,
            remarks=remarks,
        )
        return Response(InventoryReplenishmentSerializer(rep).data, status=status.HTTP_201_CREATED)


class InventoryReplenishmentViewSet(viewsets.ModelViewSet):
    """Review and approve inventory replenishment (CFR-VH-013)."""

    queryset = InventoryReplenishment.objects.select_related("item").all()
    serializer_class = InventoryReplenishmentSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """VH In-Charge approves replenishment (AFR-VH-074)."""
        rep = self.get_object()
        rep.status = ReplenishmentStatus.APPROVED
        rep.item.current_quantity += rep.quantity_requested
        rep.item.save()
        rep.save()
        return Response(InventoryReplenishmentSerializer(rep).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """VH In-Charge rejects replenishment."""
        rep = self.get_object()
        rep.status = ReplenishmentStatus.REJECTED
        rep.save()
        return Response(InventoryReplenishmentSerializer(rep).data)
