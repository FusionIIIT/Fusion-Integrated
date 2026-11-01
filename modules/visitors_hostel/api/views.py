from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.visitors_hostel.api import serializers as s
from modules.visitors_hostel.models import (
    Bill, Booking, InventoryItem, NotificationOutbox, ReplenishmentRequest, Room, Tariff)
from modules.visitors_hostel.selectors.bookings import visible_bookings
from modules.visitors_hostel.services import billing, bookings, inventory, reports
from modules.visitors_hostel.services import meals

MODULE = HasModuleGrant("visitor_hostel")


class BookingListCreateView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.booking.view", "visitor_hostel.booking.view_self",
        "visitor_hostel.booking.create")]

    def get(self, request):
        rows = visible_bookings(request.principal).order_by("-created_at")[:100]
        return Response(s.BookingSerializer(rows, many=True).data)

    def post(self, request):
        payload = s.BookingWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        booking = bookings.create_booking(actor=request.principal,
                                          data=payload.validated_data, source="online")
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class OfflineBookingView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.booking.record_offline")]

    def post(self, request):
        payload = s.BookingWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        booking = bookings.create_booking(actor=request.principal,
                                          data=payload.validated_data, source="offline")
        return Response(s.BookingSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingActionView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.booking.review", "visitor_hostel.booking.decide",
        "visitor_hostel.booking.cancel_self", "visitor_hostel.booking.modify_self",
        "visitor_hostel.room.manage",
        "visitor_hostel.stay.manage")]

    def post(self, request, pk, action):
        if action in ("review", "decision", "cancel-confirm"):
            payload = s.ActionSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            data = payload.validated_data
        elif action == "modify-request":
            payload = s.ModificationRequestSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            data = payload.validated_data
        else:
            data = request.data
        actor = request.principal
        if action == "review":
            row = bookings.review_booking(booking_id=pk, actor=actor,
                outcome=data.get("outcome"), note=data.get("note", ""))
        elif action == "decision":
            row = bookings.decide_booking(booking_id=pk, actor=actor,
                decision=data.get("decision"), note=data.get("note", ""))
        elif action == "cancel-request":
            row = bookings.request_cancellation(booking_id=pk, actor=actor)
        elif action == "modify-request":
            row = bookings.request_modification(booking_id=pk, actor=actor,
                requested_changes=data["requested_changes"])
            return Response({"id": row.pk, "booking_id": row.booking_id,
                             "status": row.status, "requested_changes": row.requested_changes},
                            status=201)
        elif action == "cancel-confirm":
            row = bookings.confirm_cancellation(booking_id=pk, actor=actor,
                confirm=data.get("confirm", False), note=data.get("note", ""))
        elif action == "allot":
            payload = s.AllocationSerializer(data=request.data)
            payload.is_valid(raise_exception=True)
            bookings.allot_rooms(booking_id=pk, actor=actor,
                                 room_ids=payload.validated_data["room_ids"])
            row = Booking.objects.get(pk=pk)
        elif action == "check-in":
            row = bookings.record_check_in(booking_id=pk, actor=actor)
        elif action == "check-out":
            row = bookings.record_check_out(booking_id=pk, actor=actor,
                bill_verified=request.data.get("bill_verified", False))
        else:
            return Response({"error": "Unknown booking action."}, status=404)
        return Response(s.BookingSerializer(row).data)


class RoomListView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.booking.view", "visitor_hostel.booking.view_self")]

    def get(self, request):
        rows = Room.objects.filter(active=True, building__is_active=True).select_related(
            "building", "room_type").order_by("building__name", "room_number")
        return Response(s.RoomSerializer(rows, many=True).data)


class RoomAvailabilityView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.booking.view", "visitor_hostel.booking.view_self",
        "visitor_hostel.booking.create")]

    def get(self, request):
        from datetime import date
        from modules.visitors_hostel.services.bookings import _available_rooms
        try:
            arrival = date.fromisoformat(request.query_params["arrival"])
            departure = date.fromisoformat(request.query_params["departure"])
        except (KeyError, ValueError):
            return Response({"error": "Valid arrival and departure dates are required."},
                            status=400)
        if departure <= arrival:
            return Response({"error": "Departure must be after arrival."}, status=400)
        rooms = _available_rooms(
            arrival=arrival, departure=departure,
            occupancy=request.query_params.get("occupancy", "single"),
            room_kind=request.query_params.get("room_kind", "non_suite"))
        return Response({"count": rooms.count()})


class TariffListCreateView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.booking.view", "visitor_hostel.tariff.manage")]

    def get(self, request):
        rows = Tariff.objects.filter(active=True).order_by(
            "visitor_category", "occupancy", "-effective_from")
        return Response(s.TariffSerializer(rows, many=True).data)

    def post(self, request):
        self.check_object_permissions(request, None)
        if not request.principal.has_permission("visitor_hostel.tariff.manage"):
            return Response(status=403)
        payload = s.TariffSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = payload.save()
        return Response(s.TariffSerializer(row).data, status=201)


class BillView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.bill.manage")]

    def get(self, request):
        rows = Bill.objects.order_by("-generated_at")[:100]
        return Response(s.BillSerializer(rows, many=True).data)

    def post(self, request):
        bill = billing.generate_bill(booking_id=request.data.get("booking_id"),
                                     actor=request.principal)
        return Response(s.BillSerializer(bill).data, status=201)


class CashSettlementView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.bill.manage")]

    def post(self, request, bill_id):
        amount = request.data.get("amount")
        row = billing.record_cash_settlement(
            bill_id=bill_id, actor=request.principal, amount=amount,
            reference_note=request.data.get("reference_note", ""))
        return Response({"id": row.pk, "bill_id": row.bill_id,
                         "amount": str(row.amount), "received_at": row.received_at}, status=201)


class MealBookingView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.meal.manage")]

    def post(self, request):
        payload = s.MealBookingWriteSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = meals.create_meal_booking(
            booking_id=data["booking_id"], actor=request.principal,
            meal_date=data["meal_date"], options=data["options"],
            add_ons=data.get("add_ons", []), quantity=data["quantity"])
        return Response(s.MealBookingSerializer(row).data, status=201)


class InventoryView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.inventory.manage", "visitor_hostel.inventory.approve")]

    def get(self, request):
        rows = InventoryItem.objects.filter(active=True).order_by("name")
        return Response(s.InventoryItemSerializer(rows, many=True).data)

    def post(self, request):
        payload = s.InventoryItemSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        data = payload.validated_data
        row = inventory.create_item(actor=request.principal, name=data["name"],
            current_quantity=data["current_quantity"],
            minimum_threshold=data["minimum_threshold"], unit=data["unit"])
        return Response(s.InventoryItemSerializer(row).data, status=201)


class InventoryChangeView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.inventory.manage")]

    def post(self, request, item_id):
        payload = s.InventoryChangeSerializer(data=request.data)
        payload.is_valid(raise_exception=True)
        row = inventory.change_quantity(item_id=item_id, actor=request.principal,
            delta=payload.validated_data["delta"],
            note=payload.validated_data.get("note", ""))
        return Response(s.InventoryItemSerializer(row).data)


class ReplenishmentView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.inventory.manage", "visitor_hostel.inventory.approve")]

    def get(self, request):
        rows = ReplenishmentRequest.objects.select_related("item").order_by("-created_at")[:100]
        return Response(s.ReplenishmentSerializer(rows, many=True).data)

    def post(self, request):
        row = inventory.create_replenishment_request(
            item_id=request.data.get("item_id"), actor=request.principal,
            quantity=request.data.get("requested_quantity", 0))
        return Response(s.ReplenishmentSerializer(row).data, status=201)


class ReplenishmentReviewView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.inventory.approve")]

    def post(self, request, pk):
        row = inventory.review_replenishment(
            request_id=pk, actor=request.principal,
            approve=bool(request.data.get("approve")),
            note=request.data.get("note", ""))
        return Response(s.ReplenishmentSerializer(row).data)


class ReportView(APIView):
    permission_classes = [MODULE, HasPermission(
        "visitor_hostel.report.view_caretaker", "visitor_hostel.report.view_in_charge")]

    def get(self, request):
        result = reports.build_report(actor=request.principal,
                                      report_type=request.query_params.get("type", ""))
        return Response(result)


class NotificationListView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.notification.view_self")]

    def get(self, request):
        rows = NotificationOutbox.objects.filter(
            recipient_user_id=request.principal.user_id).order_by("-created_at")[:100]
        return Response([{"id": r.pk, "topic": r.topic, "subject": r.subject,
                          "body": r.body, "status": r.status,
                          "created_at": r.created_at} for r in rows])


class OperationalRoleView(APIView):
    permission_classes = [MODULE, HasPermission("visitor_hostel.role.view")]

    def get(self, request):
        from modules.visitors_hostel.models import OperationalRoleAssignment
        rows = OperationalRoleAssignment.objects.order_by("role", "-starts_at")
        return Response([{"role": r.role, "user_id": r.user_id,
                          "starts_at": r.starts_at, "ends_at": r.ends_at}
                         for r in rows])
