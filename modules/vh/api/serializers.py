# Serializers and DTOs for VHMS API layer.
from decimal import Decimal

from rest_framework import serializers

from modules.vh.domain.rules import (
    BILLING_RESPONSIBILITY_CHOICES,
    OCCUPANCY_CHOICES,
    VISITOR_CATEGORY_CHOICES,
)
from modules.vh.models.bill import Bill, BillLineItem, BillSettlement
from modules.vh.models.booking import Booking
from modules.vh.models.inventory import InventoryItem, InventoryReplenishment
from modules.vh.models.meal import MealBooking
from modules.vh.models.room import Room, RoomAllotment
from modules.vh.models.tariff import TariffConfig
from modules.vh.models.visitor import VisitorDetail


class VisitorDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorDetail
        fields = ["id", "name", "email", "phone", "organization", "designation", "gender"]


class BookingCreateSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=120, required=True)
    visitor_email = serializers.EmailField(required=False, default="")
    visitor_phone = serializers.CharField(max_length=20, required=False, default="")
    visitor_category = serializers.ChoiceField(choices=VISITOR_CATEGORY_CHOICES, default="A")
    visit_purpose = serializers.CharField()
    arrival_date = serializers.DateField()
    departure_date = serializers.DateField()
    number_of_rooms = serializers.IntegerField(min_value=1, default=1)
    number_of_occupants = serializers.IntegerField(min_value=1, default=1)
    billing_responsibility = serializers.ChoiceField(
        choices=BILLING_RESPONSIBILITY_CHOICES,
        default="visitor",
    )
    visitors = VisitorDetailSerializer(many=True, required=False)


class OfflineBookingCreateSerializer(serializers.Serializer):
    booking_source = serializers.ChoiceField(choices=["telephonic", "walk_in"])
    visitor_name = serializers.CharField(max_length=120)
    visitor_email = serializers.EmailField(required=False, default="")
    visitor_phone = serializers.CharField(max_length=20, required=False, default="")
    visitor_category = serializers.ChoiceField(choices=VISITOR_CATEGORY_CHOICES, default="A")
    visit_purpose = serializers.CharField()
    arrival_date = serializers.DateField()
    departure_date = serializers.DateField()
    number_of_rooms = serializers.IntegerField(min_value=1, default=1)
    number_of_occupants = serializers.IntegerField(min_value=1, default=1)
    billing_responsibility = serializers.ChoiceField(
        choices=BILLING_RESPONSIBILITY_CHOICES,
        default="visitor",
    )
    indenter_id = serializers.IntegerField(required=False)


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "room_number", "room_type", "floor", "capacity", "is_active"]


class RoomAllotmentSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)

    class Meta:
        model = RoomAllotment
        fields = ["id", "room", "occupancy_type", "allotted_by", "allotted_at"]


class BookingDetailSerializer(serializers.ModelSerializer):
    visitors = VisitorDetailSerializer(many=True, read_only=True)
    allotments = RoomAllotmentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_reference",
            "indenter_id",
            "is_offline",
            "booking_source",
            "status",
            "visitor_category",
            "visit_purpose",
            "arrival_date",
            "departure_date",
            "checkin_time",
            "checkout_time",
            "number_of_rooms",
            "number_of_occupants",
            "billing_responsibility",
            "rejection_reason",
            "cancellation_reason",
            "cancellation_charge_percentage",
            "cancellation_requested_at",
            "cancellation_confirmed_at",
            "visitors",
            "allotments",
            "created_at",
        ]


class BookingRouteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["reject", "forward"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingDecideSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingCancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class BookingModifySerializer(serializers.Serializer):
    arrival_date = serializers.DateField(required=False)
    departure_date = serializers.DateField(required=False)
    visit_purpose = serializers.CharField(required=False)
    number_of_rooms = serializers.IntegerField(min_value=1, required=False)
    number_of_occupants = serializers.IntegerField(min_value=1, required=False)
    billing_responsibility = serializers.ChoiceField(
        choices=BILLING_RESPONSIBILITY_CHOICES,
        required=False,
    )


class RoomAllotmentCreateSerializer(serializers.Serializer):
    room_ids = serializers.ListField(child=serializers.IntegerField(), allow_empty=False)
    occupancy_type = serializers.ChoiceField(choices=OCCUPANCY_CHOICES)


class CheckInSerializer(serializers.Serializer):
    checkin_time = serializers.DateTimeField(required=False)


class CheckOutSerializer(serializers.Serializer):
    checkout_time = serializers.DateTimeField(required=False)
    verified_by_guest = serializers.BooleanField(default=True)


class MealBookingCreateSerializer(serializers.Serializer):
    meal_date = serializers.DateField()
    meal_option = serializers.ChoiceField(choices=["full_day", "individual", "add_on"])
    individual_type = serializers.ChoiceField(
        choices=["breakfast", "lunch", "dinner"], required=False, allow_null=True
    )
    add_on_type = serializers.ChoiceField(choices=["tea", "milk"], required=False, allow_null=True)
    quantity = serializers.IntegerField(min_value=1, default=1)


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = [
            "id",
            "booking_id",
            "meal_date",
            "meal_option",
            "individual_type",
            "add_on_type",
            "quantity",
            "rate",
            "amount",
            "created_at",
        ]


class BillLineItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillLineItem
        fields = ["id", "item_type", "description", "quantity", "unit_price", "total_price"]


class BillSettlementSerializer(serializers.ModelSerializer):
    class Meta:
        model = BillSettlement
        fields = [
            "id",
            "payment_mode",
            "amount_paid",
            "settled_by",
            "settled_at",
            "receipt_number",
            "notes",
        ]


class BillDetailSerializer(serializers.ModelSerializer):
    items = BillLineItemSerializer(many=True, read_only=True)
    settlement = BillSettlementSerializer(read_only=True)

    class Meta:
        model = Bill
        fields = [
            "id",
            "booking_id",
            "bill_number",
            "visitor_category",
            "room_rent_total",
            "meal_charge_total",
            "cancellation_charge_total",
            "total_amount",
            "billing_responsibility",
            "status",
            "is_immutable",
            "verified_by",
            "verified_at",
            "created_at",
            "finalized_at",
            "items",
            "settlement",
        ]


class BillSettlementCreateSerializer(serializers.Serializer):
    amount_paid = serializers.DecimalField(
        max_digits=10, decimal_places=2, min_value=Decimal("0.01")
    )
    receipt_number = serializers.CharField(max_length=50, required=False, default="")
    notes = serializers.CharField(required=False, allow_blank=True, default="")


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "item_name",
            "category",
            "current_quantity",
            "minimum_threshold",
            "unit",
            "is_threshold_alert",
            "created_at",
        ]


class InventoryReplenishmentCreateSerializer(serializers.Serializer):
    requested_quantity = serializers.IntegerField(min_value=1)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class InventoryReplenishmentSerializer(serializers.ModelSerializer):
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = InventoryReplenishment
        fields = [
            "id",
            "item",
            "requested_quantity",
            "status",
            "requested_by",
            "approved_by",
            "approved_at",
            "remarks",
            "created_at",
        ]


class InventoryReplenishmentApproveSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class TariffConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = TariffConfig
        fields = [
            "id",
            "category",
            "room_type",
            "occupancy",
            "daily_rate",
            "effective_from",
            "is_active",
        ]


class RoleReassignmentSerializer(serializers.Serializer):
    role_name = serializers.ChoiceField(choices=["caretaker", "incharge"])
    new_user_id = serializers.IntegerField()
    valid_from = serializers.DateTimeField(required=False)
    valid_to = serializers.DateTimeField(required=False, allow_null=True)
