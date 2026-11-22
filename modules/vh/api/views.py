# Views for VHMS REST API.
from datetime import date

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from core.api.exceptions import BadRequestError
from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.vh.api import serializers as s
from modules.vh.selectors import billing as billing_selectors
from modules.vh.selectors import bookings as booking_selectors
from modules.vh.selectors import inventory as inventory_selectors
from modules.vh.selectors import meals as meal_selectors
from modules.vh.selectors import reports as report_selectors
from modules.vh.selectors import rooms as room_selectors
from modules.vh.selectors import tariffs as tariff_selectors
from modules.vh.services import billing as billing_services
from modules.vh.services import booking_lifecycle as booking_services
from modules.vh.services import inventory as inventory_services
from modules.vh.services import meals as meal_services
from modules.vh.services import roles as role_services
from modules.vh.services import stays as stay_services

MODULE = HasModuleGrant("vh")


class BookingListCreateView(APIView):
    # Lists visible bookings or submits a new online requisition.
    throttle_scope = "vh_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("vh.booking.create")()]
        return [MODULE(), HasPermission("vh.booking.view")()]

    @extend_schema(
        parameters=[
            OpenApiParameter("status", str, description="Filter by status"),
            OpenApiParameter("is_offline", bool, description="Filter offline bookings"),
        ],
        responses={200: s.BookingDetailSerializer(many=True)},
    )
    def get(self, request):
        status_param = request.query_params.get("status")
        offline_param = request.query_params.get("is_offline")
        is_offline = None
        if offline_param is not None:
            is_offline = offline_param.lower() in {"true", "1"}
        bookings = booking_selectors.list_bookings(
            request.principal, status=status_param, is_offline=is_offline
        )
        serializer = s.BookingDetailSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    @extend_schema(request=s.BookingCreateSerializer, responses={201: s.BookingDetailSerializer})
    def post(self, request):
        serializer = s.BookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.create_online_booking(
            serializer.validated_data, request.principal
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_201_CREATED)


class OfflineBookingCreateView(APIView):
    # Caretaker records walk-in or telephonic bookings.
    permission_classes = [MODULE, HasPermission("vh.booking.review")]
    throttle_scope = "vh_write"

    @extend_schema(
        request=s.OfflineBookingCreateSerializer, responses={201: s.BookingDetailSerializer}
    )
    def post(self, request):
        serializer = s.OfflineBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.create_offline_booking(
            serializer.validated_data, request.principal
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_201_CREATED)


class BookingDetailView(APIView):
    # Details of a visible booking or 404.
    permission_classes = [MODULE, HasPermission("vh.booking.view")]

    @extend_schema(responses={200: s.BookingDetailSerializer})
    def get(self, request, booking_id: int):
        booking = booking_selectors.get_booking_detail(booking_id, request.principal)
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingRouteView(APIView):
    # Caretaker rejects or forwards a pending booking.
    permission_classes = [MODULE, HasPermission("vh.booking.review")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.BookingRouteSerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.BookingRouteSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.caretaker_route_booking(
            booking_id,
            serializer.validated_data["action"],
            request.principal,
            serializer.validated_data.get("reason", ""),
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingDecideView(APIView):
    # VH In-Charge approves or rejects a forwarded booking.
    permission_classes = [MODULE, HasPermission("vh.booking.approve")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.BookingDecideSerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.BookingDecideSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.incharge_decide_booking(
            booking_id,
            serializer.validated_data["action"],
            request.principal,
            serializer.validated_data.get("reason", ""),
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingCancelView(APIView):
    # Indenter requests cancellation before arrival.
    permission_classes = [MODULE, HasPermission("vh.booking.delete")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.BookingCancelSerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.BookingCancelSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.request_cancellation(
            booking_id, serializer.validated_data.get("reason", ""), request.principal
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingConfirmCancellationView(APIView):
    # Caretaker confirms booking cancellation and generates cancellation bill.
    permission_classes = [MODULE, HasPermission("vh.booking.review")]
    throttle_scope = "vh_write"

    @extend_schema(request=None, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        booking = booking_services.confirm_cancellation(booking_id, request.principal)
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingModifyView(APIView):
    # Indenter requests booking modification before arrival.
    permission_classes = [MODULE, HasPermission("vh.booking.update")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.BookingModifySerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.BookingModifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = booking_services.request_booking_modification(
            booking_id, serializer.validated_data, request.principal
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class RoomAvailabilityView(APIView):
    # Checks available rooms between arrival and departure dates.
    permission_classes = [MODULE, HasPermission("vh.booking.review")]

    @extend_schema(
        parameters=[
            OpenApiParameter("arrival_date", str, required=True),
            OpenApiParameter("departure_date", str, required=True),
            OpenApiParameter("room_type", str, required=False),
        ],
        responses={200: s.RoomSerializer(many=True)},
    )
    def get(self, request):
        arr_str = request.query_params.get("arrival_date")
        dep_str = request.query_params.get("departure_date")
        if not arr_str or not dep_str:
            raise BadRequestError("Both arrival_date and departure_date are required.")
        try:
            arr = date.fromisoformat(arr_str)
            dep = date.fromisoformat(dep_str)
        except ValueError:
            raise BadRequestError("Invalid date format. Use YYYY-MM-DD.") from None
        rtype = request.query_params.get("room_type")
        rooms = room_selectors.check_room_availability(arr, dep, rtype)
        return Response(s.RoomSerializer(rooms, many=True).data, status=status.HTTP_200_OK)


class RoomAllotmentView(APIView):
    # Caretaker allots approved rooms to a booking.
    permission_classes = [MODULE, HasPermission("vh.room.assign")]
    throttle_scope = "vh_write"

    @extend_schema(
        request=s.RoomAllotmentCreateSerializer,
        responses={200: s.RoomAllotmentSerializer(many=True)},
    )
    def post(self, request, booking_id: int):
        serializer = s.RoomAllotmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        allotments = stay_services.allot_rooms(
            booking_id,
            serializer.validated_data["room_ids"],
            serializer.validated_data["occupancy_type"],
            request.principal,
        )
        return Response(
            s.RoomAllotmentSerializer(allotments, many=True).data, status=status.HTTP_200_OK
        )


class CheckInView(APIView):
    # Records guest check-in.
    permission_classes = [MODULE, HasPermission("vh.stay.manage")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.CheckInSerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.CheckInSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = stay_services.record_checkin(
            booking_id, serializer.validated_data.get("checkin_time"), request.principal
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class CheckOutView(APIView):
    # Records guest check-out and checkout bill verification.
    permission_classes = [MODULE, HasPermission("vh.stay.manage")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.CheckOutSerializer, responses={200: s.BookingDetailSerializer})
    def post(self, request, booking_id: int):
        serializer = s.CheckOutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        booking = stay_services.record_checkout(
            booking_id,
            serializer.validated_data.get("checkout_time"),
            serializer.validated_data.get("verified_by_guest", True),
            request.principal,
        )
        return Response(s.BookingDetailSerializer(booking).data, status=status.HTTP_200_OK)


class BookingMealsListCreateView(APIView):
    # Lists or books meals for a staying guest.
    throttle_scope = "vh_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("vh.meal.manage")()]
        return [MODULE(), HasPermission("vh.meal.view")()]

    @extend_schema(responses={200: s.MealBookingSerializer(many=True)})
    def get(self, request, booking_id: int):
        meals = meal_selectors.list_booking_meals(booking_id, request.principal)
        return Response(s.MealBookingSerializer(meals, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(request=s.MealBookingCreateSerializer, responses={201: s.MealBookingSerializer})
    def post(self, request, booking_id: int):
        serializer = s.MealBookingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        meal = meal_services.book_meal(
            booking_id=booking_id,
            meal_date=vd["meal_date"],
            meal_option=vd["meal_option"],
            individual_type=vd.get("individual_type"),
            add_on_type=vd.get("add_on_type"),
            quantity=vd.get("quantity", 1),
            principal=request.principal,
        )
        return Response(s.MealBookingSerializer(meal).data, status=status.HTTP_201_CREATED)


class BillDetailGenerateView(APIView):
    # Views or triggers bill generation for a booking.
    throttle_scope = "vh_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("vh.bill.create")()]
        return [MODULE(), HasPermission("vh.bill.view")()]

    @extend_schema(responses={200: s.BillDetailSerializer})
    def get(self, request, booking_id: int):
        bill = billing_selectors.get_bill_for_booking(booking_id, request.principal)
        return Response(s.BillDetailSerializer(bill).data, status=status.HTTP_200_OK)

    @extend_schema(request=None, responses={201: s.BillDetailSerializer})
    def post(self, request, booking_id: int):
        bill = billing_services.generate_bill(booking_id, request.principal)
        return Response(s.BillDetailSerializer(bill).data, status=status.HTTP_201_CREATED)


class BillSettlementView(APIView):
    # Records offline cash settlement of a bill.
    permission_classes = [MODULE, HasPermission("vh.bill.manage")]
    throttle_scope = "vh_write"

    @extend_schema(
        request=s.BillSettlementCreateSerializer, responses={200: s.BillSettlementSerializer}
    )
    def post(self, request, bill_id: int):
        serializer = s.BillSettlementCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        settlement = billing_services.record_offline_settlement(
            bill_id=bill_id,
            amount_paid=vd["amount_paid"],
            receipt_number=vd.get("receipt_number", ""),
            notes=vd.get("notes", ""),
            principal=request.principal,
        )
        return Response(s.BillSettlementSerializer(settlement).data, status=status.HTTP_200_OK)


class InventoryListCreateView(APIView):
    # Lists inventory items or creates/updates inventory records.
    throttle_scope = "vh_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("vh.inventory.manage")()]
        return [MODULE(), HasPermission("vh.inventory.view")()]

    @extend_schema(
        parameters=[OpenApiParameter("category", str, required=False)],
        responses={200: s.InventoryItemSerializer(many=True)},
    )
    def get(self, request):
        cat = request.query_params.get("category")
        items = inventory_selectors.list_inventory_items(cat)
        return Response(s.InventoryItemSerializer(items, many=True).data, status=status.HTTP_200_OK)

    @extend_schema(request=s.InventoryItemSerializer, responses={200: s.InventoryItemSerializer})
    def post(self, request):
        serializer = s.InventoryItemSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = inventory_services.save_inventory_item(serializer.validated_data, request.principal)
        return Response(s.InventoryItemSerializer(item).data, status=status.HTTP_200_OK)


class InventoryReplenishRequestView(APIView):
    # Caretaker submits replenishment request.
    permission_classes = [MODULE, HasPermission("vh.inventory.manage")]
    throttle_scope = "vh_write"

    @extend_schema(
        request=s.InventoryReplenishmentCreateSerializer,
        responses={201: s.InventoryReplenishmentSerializer},
    )
    def post(self, request, item_id: int):
        serializer = s.InventoryReplenishmentCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = inventory_services.request_replenishment(
            item_id,
            serializer.validated_data["requested_quantity"],
            serializer.validated_data.get("remarks", ""),
            request.principal,
        )
        return Response(
            s.InventoryReplenishmentSerializer(req).data, status=status.HTTP_201_CREATED
        )


class InventoryReplenishApproveView(APIView):
    # VH In-Charge approves or rejects replenishment request.
    permission_classes = [MODULE, HasPermission("vh.inventory.approve")]
    throttle_scope = "vh_write"

    @extend_schema(
        request=s.InventoryReplenishmentApproveSerializer,
        responses={200: s.InventoryReplenishmentSerializer},
    )
    def post(self, request, replenishment_id: int):
        serializer = s.InventoryReplenishmentApproveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        req = inventory_services.approve_replenishment(
            replenishment_id,
            serializer.validated_data["decision"],
            serializer.validated_data.get("remarks", ""),
            request.principal,
        )
        return Response(s.InventoryReplenishmentSerializer(req).data, status=status.HTTP_200_OK)


class TariffListCreateView(APIView):
    # Lists tariffs or creates new effective-dated tariff card.
    throttle_scope = "vh_write"

    def get_permissions(self):
        if self.request.method == "POST":
            return [MODULE(), HasPermission("vh.tariff.manage")()]
        return [MODULE(), HasPermission("vh.tariff.view")()]

    @extend_schema(responses={200: s.TariffConfigSerializer(many=True)})
    def get(self, request):
        tariffs = tariff_selectors.list_tariffs(active_only=True)
        return Response(
            s.TariffConfigSerializer(tariffs, many=True).data, status=status.HTTP_200_OK
        )

    @extend_schema(request=s.TariffConfigSerializer, responses={201: s.TariffConfigSerializer})
    def post(self, request):
        serializer = s.TariffConfigSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tariff = serializer.save()
        return Response(s.TariffConfigSerializer(tariff).data, status=status.HTTP_201_CREATED)


class CaretakerReportsView(APIView):
    # Operational reports for hostel Caretaker.
    permission_classes = [MODULE, HasPermission("vh.report.view")]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "report_type",
                str,
                required=True,
                description="occupancy|arrivals|pending|exceptions",
            ),
            OpenApiParameter("date", str, required=False),
        ],
        responses={200: dict},
    )
    def get(self, request):
        rtype = request.query_params.get("report_type", "occupancy").lower()
        d_str = request.query_params.get("date")
        target_date = date.fromisoformat(d_str) if d_str else date.today()

        if rtype == "occupancy":
            data = report_selectors.get_daily_occupancy_report(target_date)
        elif rtype == "arrivals":
            data = report_selectors.get_arrivals_departures_report(target_date)
        elif rtype == "pending":
            data = report_selectors.get_pending_approvals_report()
        elif rtype == "exceptions":
            data = report_selectors.get_stay_exception_logs()
        else:
            raise BadRequestError(
                f"Unknown report_type '{rtype}'. Allowed: occupancy, arrivals, pending, exceptions."
            )
        return Response(data, status=status.HTTP_200_OK)


class InchargeReportsView(APIView):
    # Supervisory summary reports for VH In-Charge.
    permission_classes = [MODULE, HasPermission("vh.report.manage")]

    @extend_schema(
        parameters=[
            OpenApiParameter(
                "report_type", str, required=True, description="summary|occupancy|revenue|inventory"
            )
        ],
        responses={200: dict},
    )
    def get(self, request):
        rtype = request.query_params.get("report_type", "summary").lower()
        if rtype == "summary":
            data = report_selectors.get_booking_summary_report()
        elif rtype == "occupancy":
            data = report_selectors.get_category_occupancy_report()
        elif rtype == "revenue":
            data = report_selectors.get_revenue_summary_report()
        elif rtype == "inventory":
            data = report_selectors.get_inventory_usage_report()
        else:
            raise BadRequestError(
                f"Unknown report_type '{rtype}'. Allowed: summary, occupancy, revenue, inventory."
            )
        return Response(data, status=status.HTTP_200_OK)


class RoleReassignmentView(APIView):
    # Reassigns operational Caretaker or In-Charge role.
    permission_classes = [MODULE, HasPermission("vh.role.assign")]
    throttle_scope = "vh_write"

    @extend_schema(request=s.RoleReassignmentSerializer, responses={200: dict})
    def post(self, request):
        serializer = s.RoleReassignmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        vd = serializer.validated_data
        holder = role_services.reassign_operational_role(
            role_name=vd["role_name"],
            new_user_id=vd["new_user_id"],
            valid_from=vd.get("valid_from"),
            valid_to=vd.get("valid_to"),
            principal=request.principal,
        )
        return Response(
            {
                "id": holder.id,
                "role_name": holder.role_name,
                "user_id": holder.user_id,
                "is_active": holder.is_active,
                "valid_from": holder.valid_from.isoformat(),
            },
            status=status.HTTP_200_OK,
        )
