"""API views for Visitors Hostel (VH) module."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from modules.vh.api.serializers import (
    BillSerializer,
    BookingActionSerializer,
    BookingModificationSerializer,
    BookingSerializer,
    InventoryItemSerializer,
    InventoryReplenishmentSerializer,
    MealBookingSerializer,
    RoomSerializer,
    TariffSerializer,
    VHAlertSerializer,
    VHNotificationLogSerializer,
    VHMSUserRoleSerializer,
    VisitorCategorySerializer,
)
from modules.vh.models import (
    Bill,
    Booking,
    BookingModification,
    BookingStatus,
    InventoryItem,
    InventoryReplenishment,
    MealBooking,
    ModificationStatus,
    ReplenishmentStatus,
    Room,
    RoomAllotment,
    RoomStatus,
    Tariff,
    VHAlert,
    VHNotificationEventType,
    VHNotificationLog,
    VisitorCategory,
    VHMSUserRole,
    VHMSUserRoleType,
)
from modules.vh.services.notifications import (
    check_inventory_threshold_alert,
    check_stay_exception_alerts,
    emit_booking_lifecycle_notification,
)
from modules.vh.services.reports import get_caretaker_reports, get_incharge_reports


class VisitorCategoryViewSet(viewsets.ModelViewSet):
    """View and manage visitor categories (CFR-VH-009, BR-VH-019)."""

    queryset = VisitorCategory.objects.all()
    serializer_class = VisitorCategorySerializer
    permission_classes = [permissions.AllowAny]


class RoomViewSet(viewsets.ModelViewSet):
    """View and manage hostel rooms (CFR-VH-007, BR-VH-013..016)."""

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

    @action(detail=False, methods=["get"])
    def availability(self, request):
        """Check room availability across date range for Caretaker review (BR-VH-004, UC-VH-003)."""
        check_in_str = request.query_params.get("check_in")
        check_out_str = request.query_params.get("check_out")
        room_type = request.query_params.get("room_type")

        qs = Room.objects.filter(status=RoomStatus.AVAILABLE)
        if room_type:
            qs = qs.filter(room_type=room_type.upper())

        if check_in_str and check_out_str:
            try:
                check_in = timezone.datetime.strptime(check_in_str, "%Y-%m-%d").date()
                check_out = timezone.datetime.strptime(check_out_str, "%Y-%m-%d").date()
                # Exclude rooms that have active overlapping allotments
                busy_room_ids = RoomAllotment.objects.filter(
                    booking__status__in=[
                        BookingStatus.ROOM_ALLOTTED,
                        BookingStatus.CHECKED_IN,
                    ],
                    booking__check_in_date__lt=check_out,
                    booking__check_out_date__gt=check_in,
                ).values_list("room_id", flat=True)
                qs = qs.exclude(id__in=busy_room_ids)
            except ValueError:
                return Response(
                    {"error": "Invalid date format; use YYYY-MM-DD."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        return Response(RoomSerializer(qs, many=True).data)


class TariffViewSet(viewsets.ModelViewSet):
    """View and manage tariff structure (CFR-VH-009, BR-VH-023, BR-VH-024)."""

    queryset = Tariff.objects.all()
    serializer_class = TariffSerializer
    permission_classes = [permissions.AllowAny]


class BookingViewSet(viewsets.ModelViewSet):
    """Lifecycle and management of visitor hostel bookings.

    Covers Indenter submissions (CFR-VH-002, UC-VH-001), Caretaker review/offline booking
    (CFR-VH-003, CFR-VH-004, UC-VH-003, UC-VH-005), In-Charge approvals (UC-VH-004),
    cancellations (CFR-VH-006, UC-VH-007, UC-VH-020), room allotment (UC-VH-008),
    stay progression (BW-VH-10, UC-VH-009, UC-VH-021), and notifications (UC-VH-023).
    """

    queryset = (
        Booking.objects.select_related("visitor_category")
        .prefetch_related("allotments", "meal_bookings", "modifications")
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
        active_caretaker = VHMSUserRole.get_active_caretaker()
        caretaker_id = active_caretaker.user_id if active_caretaker else None

        booking = serializer.save(
            indenter_id=user_id,
            status=BookingStatus.PENDING,
            assigned_caretaker_id=caretaker_id,
        )

        # Trigger booking submission lifecycle notification (UC-VH-023)
        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_SUBMITTED,
        )

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

        active_incharge = VHMSUserRole.get_active_incharge()
        incharge_id = active_incharge.user_id if active_incharge else None

        booking.caretaker_remarks = action_ser.validated_data.get("remarks", "")
        booking.status = BookingStatus.FORWARDED
        booking.assigned_incharge_id = incharge_id
        booking.save()

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_FORWARDED,
        )
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def approve(self, request, pk=None):
        """VH In-Charge approves booking (CW-VH-01, AFR-VH-018, UC-VH-004)."""
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

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_APPROVED,
        )
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

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_REJECTED,
        )
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def allot_room(self, request, pk=None):
        """Allot room(s) to approved booking (BR-VH-012, BW-VH-10, UC-VH-008)."""
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
        """Record guest check-in (BW-VH-10, AFR-VH-041, UC-VH-009)."""
        booking = self.get_object()
        if booking.status != BookingStatus.ROOM_ALLOTTED:
            return Response(
                {"error": "Guest can only check in after room allotment."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        booking.allotments.update(check_in_time=now, is_no_show=False)
        booking.status = BookingStatus.CHECKED_IN
        booking.save()
        return Response(BookingSerializer(booking).data)

    @action(detail=True, methods=["post"])
    def check_out(self, request, pk=None):
        """Record guest check-out and generate bill (BW-VH-10, AFR-VH-042, CFR-VH-011, UC-VH-021)."""
        booking = self.get_object()
        if booking.status != BookingStatus.CHECKED_IN:
            return Response(
                {"error": "Guest must be checked in before checking out."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        now = timezone.now()
        booking.allotments.update(check_out_time=now, is_overstay=False)

        # Free all allotted rooms
        first_room = None
        for allotment in booking.allotments.all():
            if not first_room:
                first_room = allotment.room
            allotment.room.status = RoomStatus.AVAILABLE
            allotment.room.save()

        # Calculate stay duration
        days = max((booking.check_out_date - booking.check_in_date).days, 1)

        # BR-VH-023: Find category-specific and occupancy-specific tariff
        tariff_qs = Tariff.objects.filter(category=booking.visitor_category)
        if first_room:
            matching_tariff = tariff_qs.filter(
                room_type=first_room.room_type,
                occupancy_type=first_room.occupancy_type,
            ).order_by("-effective_from").first()
        else:
            matching_tariff = None

        if not matching_tariff:
            matching_tariff = tariff_qs.order_by("-effective_from").first()

        rate_per_day = matching_tariff.rate_per_day if matching_tariff else Decimal("500.00")
        room_charges = rate_per_day * Decimal(str(days)) * Decimal(str(booking.number_of_rooms))

        # Calculate meal charges (BR-VH-032, BR-VH-034)
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

    def _compute_cancellation_charge(self, booking: Booking) -> Decimal:
        """Compute cancellation fee per BR-VH-006, BR-VH-007, BR-VH-008, BR-VH-009."""
        today = timezone.localdate()
        days_to_arrival = (booking.check_in_date - today).days

        tariff = Tariff.objects.filter(
            category=booking.visitor_category
        ).order_by("-effective_from").first()
        one_day_rent = tariff.rate_per_day if tariff else Decimal("500.00")
        base_rent = one_day_rent * Decimal(str(booking.number_of_rooms))

        if days_to_arrival >= 7:
            return Decimal("0.00")
        elif days_to_arrival > 0:
            return (base_rent * Decimal("0.25")).quantize(Decimal("0.01"))
        else:
            return (base_rent * Decimal("0.50")).quantize(Decimal("0.01"))

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def request_cancellation(self, request, pk=None):
        """Step 1: Indenter requests booking cancellation (UC-VH-007, BW-VH-07..09, CW-VH-02)."""
        booking = self.get_object()
        terminal_statuses = (
            BookingStatus.CHECKED_IN,
            BookingStatus.CHECKED_OUT,
            BookingStatus.CANCELLED,
            BookingStatus.CANCELLATION_REQUESTED,
        )
        if booking.status in terminal_statuses:
            return Response(
                {"error": f"Cannot request cancellation for booking in '{booking.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        action_ser = BookingActionSerializer(data=request.data)
        action_ser.is_valid(raise_exception=True)
        reason = action_ser.validated_data.get("reason", "")

        charge = self._compute_cancellation_charge(booking)

        # Release any rooms that were allotted
        for allotment in booking.allotments.all():
            allotment.room.status = RoomStatus.AVAILABLE
            allotment.room.save()

        booking.status = BookingStatus.CANCELLATION_REQUESTED
        booking.cancellation_reason = reason
        booking.calculated_cancellation_charge = charge
        booking.save()

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.CANCELLATION_REQUESTED,
        )

        return Response({
            "message": f"Cancellation requested. Applicable charge: Rs {charge}.",
            "booking": BookingSerializer(booking).data,
            "applicable_cancellation_charge": str(charge),
        })

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def confirm_cancellation(self, request, pk=None):
        """Step 2: Caretaker reviews & confirms cancellation (UC-VH-020, CW-VH-02, BR-VH-011)."""
        booking = self.get_object()
        if booking.status != BookingStatus.CANCELLATION_REQUESTED:
            return Response(
                {"error": f"Cannot confirm cancellation: booking status is '{booking.status}', expected 'CANCELLATION_REQUESTED'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        charge = booking.calculated_cancellation_charge

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.cancellation_charges = charge
        bill.total_amount = charge
        bill.save()

        booking.status = BookingStatus.CANCELLED
        booking.save()

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_CANCELLED,
        )

        return Response({
            "message": f"Booking cancellation confirmed. Adjusted cancellation charge: Rs {charge}.",
            "booking": BookingSerializer(booking).data,
            "bill": BillSerializer(bill).data,
        })

    @action(detail=True, methods=["post"], serializer_class=BookingActionSerializer)
    def cancel(self, request, pk=None):
        """Convenience/direct cancellation supporting one-step or legacy requests (BR-VH-006..009)."""
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

        charge = self._compute_cancellation_charge(booking)

        for allotment in booking.allotments.all():
            allotment.room.status = RoomStatus.AVAILABLE
            allotment.room.save()

        bill, _ = Bill.objects.get_or_create(booking=booking)
        bill.cancellation_charges = charge
        bill.total_amount = charge
        bill.save()

        booking.status = BookingStatus.CANCELLED
        booking.cancellation_reason = reason
        booking.calculated_cancellation_charge = charge
        booking.save()

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.BOOKING_CANCELLED,
        )

        return Response({
            "message": f"Booking cancelled. Cancellation charge: Rs {charge}.",
            "booking": BookingSerializer(booking).data,
            "bill": BillSerializer(bill).data,
        })

    @action(detail=True, methods=["get"])
    def printable(self, request, pk=None):
        """Formatted printable booking confirmation slip (UC-VH-002, AFR-VH-003)."""
        booking = self.get_object()
        allotted_rooms = [a.room.room_number for a in booking.allotments.all()]
        bill_data = BillSerializer(booking.bill).data if hasattr(booking, "bill") else None

        slip = {
            "title": "Indian Institute of Information Technology - Visitors Hostel Booking Slip",
            "booking_reference": booking.booking_reference,
            "indenter_id": booking.indenter_id,
            "visitor_name": booking.visitor_name,
            "visitor_phone": booking.visitor_phone,
            "visitor_email": booking.visitor_email,
            "category": f"{booking.visitor_category.code} - {booking.visitor_category.name}",
            "visit_purpose": booking.visit_purpose,
            "check_in_date": str(booking.check_in_date),
            "check_out_date": str(booking.check_out_date),
            "number_of_rooms": booking.number_of_rooms,
            "status": booking.status,
            "allotted_rooms": allotted_rooms,
            "billing_responsibility": booking.billing_responsibility,
            "bill": bill_data,
            "generated_at": timezone.now().isoformat(),
        }
        return Response(slip)


class MealBookingViewSet(viewsets.ModelViewSet):
    """Manage meal bookings for residing guests (CFR-VH-010, BR-VH-025, 029, 030, 031)."""

    queryset = MealBooking.objects.select_related("booking").all()
    serializer_class = MealBookingSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        persons = serializer.validated_data.get("number_of_persons", 1)
        rate = serializer.validated_data.get("rate", Decimal("100.00"))
        total = rate * Decimal(str(persons))
        serializer.save(rate=rate, total_amount=total)


class BillViewSet(viewsets.ModelViewSet):
    """View and offline-settle bills (CFR-VH-011, BR-VH-036, BR-VH-037)."""

    queryset = Bill.objects.select_related("booking").all()
    serializer_class = BillSerializer
    permission_classes = [permissions.AllowAny]

    def update(self, request, *args, **kwargs):
        bill = self.get_object()
        if bill.is_finalized:
            return Response(
                {"error": "Finalized bills are immutable for audit per BR-VH-037."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().update(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        bill = self.get_object()
        if bill.is_finalized:
            return Response(
                {"error": "Finalized bills cannot be deleted per BR-VH-037."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().destroy(request, *args, **kwargs)

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
    """Inventory management and threshold alert monitoring (CFR-VH-012, BR-VH-041, UC-VH-014, UC-VH-025)."""

    queryset = InventoryItem.objects.all()
    serializer_class = InventoryItemSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        item = serializer.save()
        check_inventory_threshold_alert(item)

    def perform_update(self, serializer):
        item = serializer.save()
        check_inventory_threshold_alert(item)

    @action(detail=False, methods=["get"])
    def alerts(self, request):
        """Return items where current quantity is below threshold (BR-VH-041, UC-VH-025)."""
        items = [i for i in self.get_queryset() if i.is_below_threshold]
        return Response(InventoryItemSerializer(items, many=True).data)

    @action(detail=True, methods=["post"])
    def request_replenishment(self, request, pk=None):
        """Caretaker requests inventory replenishment (CFR-VH-013, UC-VH-014)."""
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
    """Review and approve inventory replenishment (CFR-VH-013, UC-VH-015)."""

    queryset = InventoryReplenishment.objects.select_related("item").all()
    serializer_class = InventoryReplenishmentSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """VH In-Charge approves replenishment (AFR-VH-074, UC-VH-015)."""
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


class BookingModificationViewSet(viewsets.ModelViewSet):
    """Booking modification requests and confirmation (UC-VH-006, UC-VH-022, BR-VH-010)."""

    queryset = BookingModification.objects.select_related("booking").all()
    serializer_class = BookingModificationSerializer
    permission_classes = [permissions.AllowAny]

    def perform_create(self, serializer):
        user_id = getattr(self.request.user, "id", None) or 1
        mod = serializer.save(requested_by_user_id=user_id, status=ModificationStatus.PENDING)
        emit_booking_lifecycle_notification(
            booking=mod.booking,
            event_type=VHNotificationEventType.MODIFICATION_REQUESTED,
        )

    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        """Record confirmed booking modification outcome (UC-VH-022, BR-VH-010)."""
        mod = self.get_object()
        if mod.status != ModificationStatus.PENDING:
            return Response(
                {"error": f"Cannot confirm modification in '{mod.status}' status."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user_id = getattr(request.user, "id", None) or 1
        remarks = request.data.get("remarks", "")
        booking = mod.booking

        # Apply modifications to booking
        if mod.new_check_in_date:
            booking.check_in_date = mod.new_check_in_date
        if mod.new_check_out_date:
            booking.check_out_date = mod.new_check_out_date
        if mod.new_number_of_rooms:
            booking.number_of_rooms = mod.new_number_of_rooms
        if mod.new_number_of_occupants:
            booking.number_of_occupants = mod.new_number_of_occupants
        booking.save()

        # Adjust billing if bill already generated (BR-VH-010)
        if hasattr(booking, "bill") and not booking.bill.is_finalized:
            days = max((booking.check_out_date - booking.check_in_date).days, 1)
            tariff = Tariff.objects.filter(
                category=booking.visitor_category
            ).order_by("-effective_from").first()
            rate = tariff.rate_per_day if tariff else Decimal("500.00")
            booking.bill.room_charges = rate * Decimal(str(days)) * Decimal(str(booking.number_of_rooms))
            booking.bill.total_amount = booking.bill.room_charges + booking.bill.meal_charges
            booking.bill.save()

        mod.status = ModificationStatus.CONFIRMED
        mod.confirmed_by_user_id = user_id
        mod.remarks = remarks
        mod.save()

        emit_booking_lifecycle_notification(
            booking=booking,
            event_type=VHNotificationEventType.MODIFICATION_CONFIRMED,
        )

        return Response(BookingModificationSerializer(mod).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Reject booking modification request."""
        mod = self.get_object()
        user_id = getattr(request.user, "id", None) or 1
        mod.status = ModificationStatus.REJECTED
        mod.confirmed_by_user_id = user_id
        mod.remarks = request.data.get("remarks", "")
        mod.save()
        return Response(BookingModificationSerializer(mod).data)


class VHMSUserRoleViewSet(viewsets.ModelViewSet):
    """Operational role assignment and active record transfers (UC-VH-019, BR-VH-045..050)."""

    queryset = VHMSUserRole.objects.all()
    serializer_class = VHMSUserRoleSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"])
    def assign(self, request):
        """Reassign operational role immediately, enforcing single active role and record transfer."""
        role_type = request.data.get("role_type")
        user_id = request.data.get("user_id")
        start_date = request.data.get("start_date")
        end_date = request.data.get("end_date")

        if not role_type or not user_id:
            return Response(
                {"error": "Both role_type and user_id are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if role_type not in (VHMSUserRoleType.CARETAKER, VHMSUserRoleType.IN_CHARGE):
            return Response(
                {"error": f"Invalid role_type '{role_type}'. Must be CARETAKER or IN_CHARGE."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        new_role = VHMSUserRole.reassign_role(
            role_type=role_type,
            user_id=int(user_id),
            start_date=start_date,
            end_date=end_date,
        )

        return Response(
            VHMSUserRoleSerializer(new_role).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["get"])
    def active(self, request):
        """Retrieve the currently active Caretaker and VH In-Charge."""
        active_caretaker = VHMSUserRole.get_active_caretaker()
        active_incharge = VHMSUserRole.get_active_incharge()
        return Response({
            "caretaker": VHMSUserRoleSerializer(active_caretaker).data if active_caretaker else None,
            "incharge": VHMSUserRoleSerializer(active_incharge).data if active_incharge else None,
        })


class VHReportViewSet(viewsets.ViewSet):
    """VH reporting subsystem for In-Charge and Caretaker (UC-VH-017, UC-VH-018, CFR-VH-015, CFR-VH-016)."""

    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["get"])
    def incharge(self, request):
        """Generate supervisory reports for VH In-Charge (UC-VH-017)."""
        data = get_incharge_reports()
        return Response(data)

    @action(detail=False, methods=["get"])
    def caretaker(self, request):
        """Generate operational reports and logs for Caretaker (UC-VH-018)."""
        data = get_caretaker_reports()
        return Response(data)


class VHAlertViewSet(viewsets.ModelViewSet):
    """Exception alerts and reminders (BR-VH-017, BR-VH-018, BR-VH-041, UC-VH-024, UC-VH-025)."""

    queryset = VHAlert.objects.all()
    serializer_class = VHAlertSerializer
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=["post"])
    def scan(self, request):
        """Trigger scan for stay exceptions (no-shows, overstays) and inventory thresholds."""
        stay_results = check_stay_exception_alerts()
        inv_alerts = 0
        for item in InventoryItem.objects.all():
            alt = check_inventory_threshold_alert(item)
            if alt:
                inv_alerts += 1

        return Response({
            "message": "Stay and inventory scan completed.",
            "no_shows_detected": stay_results["no_shows"],
            "overstays_detected": stay_results["overstays"],
            "inventory_alerts_active": inv_alerts,
        })

    @action(detail=True, methods=["post"])
    def resolve(self, request, pk=None):
        """Mark alert as resolved."""
        alert = self.get_object()
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        return Response(VHAlertSerializer(alert).data)


class VHNotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    """System-generated notification audit logs (UC-VH-023, CFR-VH-014)."""

    queryset = VHNotificationLog.objects.all()
    serializer_class = VHNotificationLogSerializer
    permission_classes = [permissions.AllowAny]
