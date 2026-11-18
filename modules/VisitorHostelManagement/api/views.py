"""API Views for Visitor Hostel Management System."""
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from fusion_auth.permissions import HasModuleGrant, HasPermission
from .. import services as svc
from ..models import Bill, Booking, InventoryItem, Notification, Room, Tariff
from . import serializers as sz

MODULE = HasModuleGrant("visitor_hostel")
P_CREATE = "visitor_hostel.booking.create"
P_VIEW_SELF = "visitor_hostel.booking.view_self"
P_CANCEL = "visitor_hostel.booking.cancel"
P_REVIEW = "visitor_hostel.booking.review"
P_ALLOT = "visitor_hostel.booking.allot"
P_CHECKIN = "visitor_hostel.booking.checkin"
P_CHECKOUT = "visitor_hostel.booking.checkout"
P_APPROVE = "visitor_hostel.booking.approve"
P_TARIFF = "visitor_hostel.tariff.manage"
P_MEAL = "visitor_hostel.meal.manage"
P_BILLING = "visitor_hostel.billing.manage"
P_INVENTORY = "visitor_hostel.inventory.manage"
P_INV_APPROVE = "visitor_hostel.inventory.approve"
P_REPORT = "visitor_hostel.report.view"


class BaseVHView(APIView):
    permission_classes = [MODULE]

    def get_actor_id(self, request) -> int:
        p = getattr(request, "principal", None)
        return p.user_id if (p and hasattr(p, "user_id")) else 1

    def handle_error(self, exc: Exception) -> Response:
        return Response({"error": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


class BookingListCreateView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF, P_CREATE)]

    def get(self, request):
        st = request.query_params.get("status")
        qs = Booking.objects.filter(status=st) if st else Booking.objects.all()
        return Response(sz.BookingSerializer(qs.order_by("-created_at")[:100], many=True).data)

    def post(self, request):
        ser = sz.BookingCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            b = svc.create_booking(indenter_id=self.get_actor_id(request), **ser.validated_data)
            return Response(sz.BookingSerializer(b).data, status=status.HTTP_201_CREATED)
        except (ValueError, TypeError, KeyError) as exc:
            return self.handle_error(exc)


class MyBookingsView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request):
        qs = Booking.objects.filter(indenter_id=self.get_actor_id(request)).order_by("-created_at")
        return Response(sz.BookingSerializer(qs, many=True).data)


class BookingDetailView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_VIEW_SELF)]

    def get(self, request, pk: int):
        b = Booking.objects.filter(pk=pk).first()
        return Response(sz.BookingSerializer(b).data) if b else Response({"error": "Not found."}, status=404)


class BookingReviewView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_REVIEW)]

    def post(self, request, pk: int):
        ser = sz.ReviewSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            b = svc.review_booking(pk, self.get_actor_id(request), ser.validated_data["action"], ser.validated_data.get("remarks", ""))
            return Response(sz.BookingSerializer(b).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BookingDecisionView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_APPROVE)]

    def post(self, request, pk: int):
        ser = sz.DecisionSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            b = svc.decide_booking(pk, self.get_actor_id(request), ser.validated_data["action"], ser.validated_data.get("remarks", ""))
            return Response(sz.BookingSerializer(b).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BookingCancelView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_CANCEL)]

    def post(self, request, pk: int):
        ser = sz.CancelSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            b = svc.cancel_booking(pk, self.get_actor_id(request), ser.validated_data.get("reason", ""))
            return Response(sz.BookingSerializer(b).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BookingAllotView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_ALLOT)]

    def post(self, request, pk: int):
        ser = sz.AllotSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            b = svc.allot_rooms(pk, ser.validated_data["room_ids"])
            return Response(sz.BookingSerializer(b).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BookingCheckInView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_CHECKIN)]

    def post(self, request, pk: int):
        try:
            return Response(sz.BookingSerializer(svc.check_in_guest(pk)).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BookingCheckOutView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_CHECKOUT)]

    def post(self, request, pk: int):
        try:
            return Response(sz.BillSerializer(svc.check_out_guest(pk)).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class MealBookingView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_MEAL)]

    def post(self, request, pk: int):
        ser = sz.MealCreateSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            m = svc.book_meal(pk, ser.validated_data["meal_date"], ser.validated_data["meal_type"], ser.validated_data.get("add_on", "none"))
            return Response(sz.MealBookingSerializer(m).data, status=status.HTTP_201_CREATED)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class BillSettleView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_BILLING)]

    def post(self, request, pk: int):
        try:
            return Response(sz.BillSerializer(svc.settle_bill(pk)).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class InventoryView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_INVENTORY)]

    def get(self, request):
        return Response(sz.InventorySerializer(InventoryItem.objects.all(), many=True).data)

    def post(self, request):
        try:
            item = svc.update_inventory(request.data.get("item_id"), int(request.data.get("quantity", 0)))
            return Response(sz.InventorySerializer(item).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class InventoryReplenishView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_INVENTORY)]

    def post(self, request, pk: int):
        try:
            item = svc.request_replenishment(pk, int(request.data.get("quantity", 10)))
            return Response(sz.InventorySerializer(item).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class InventoryApproveView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_INV_APPROVE)]

    def post(self, request, pk: int):
        try:
            return Response(sz.InventorySerializer(svc.approve_replenishment(pk)).data)
        except (ValueError, TypeError, KeyError, ObjectDoesNotExist) as exc:
            return self.handle_error(exc)


class RoleReassignView(BaseVHView):
    def post(self, request):
        ser = sz.RoleReassignSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        try:
            a = svc.reassign_role(ser.validated_data["role"], ser.validated_data["new_user_id"])
            return Response({"role": a.role, "user_id": a.user_id, "is_active": a.is_active})
        except (ValueError, TypeError, KeyError) as exc:
            return self.handle_error(exc)


class TariffListView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_TARIFF)]

    def get(self, request):
        return Response(sz.TariffSerializer(Tariff.objects.all().order_by("-effective_from"), many=True).data)

    def post(self, request):
        ser = sz.TariffSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)
        ser.save()
        return Response(ser.data, status=status.HTTP_201_CREATED)


class RoomListView(BaseVHView):
    def get(self, request):
        return Response(sz.RoomSerializer(Room.objects.all(), many=True).data)


class NotificationListView(BaseVHView):
    def get(self, request):
        return Response(sz.NotificationSerializer(Notification.objects.all().order_by("-created_at")[:50], many=True).data)


class CaretakerReportsView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_REPORT)]

    def get(self, request):
        today = timezone.now().date()
        return Response({
            "daily_occupancy": Room.objects.filter(status="occupied").count(),
            "upcoming_arrivals": Booking.objects.filter(status="approved", check_in_date__gte=today).count(),
            "upcoming_departures": Booking.objects.filter(status="checked_in", check_out_date__gte=today).count(),
            "pending_approvals": Booking.objects.filter(status="pending").count(),
            "no_shows": Booking.objects.filter(status="approved", check_in_date__lt=today).count(),
            "overstays": Booking.objects.filter(status="checked_in", check_out_date__lt=today).count(),
        })


class InchargeReportsView(BaseVHView):
    permission_classes = [MODULE, HasPermission(P_REPORT)]

    def get(self, request):
        return Response({
            "total_bookings": Booking.objects.count(),
            "approved_bookings": Booking.objects.filter(status="approved").count(),
            "rejected_bookings": Booking.objects.filter(status="rejected").count(),
            "total_revenue": str(sum((b.total_amount for b in Bill.objects.filter(is_settled=True)), 0)),
            "low_stock_items": InventoryItem.objects.filter(quantity__lte=10).count(),
        })
