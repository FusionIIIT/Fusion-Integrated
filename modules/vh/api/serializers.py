"""Serializers for the Visitors Hostel (VH) API."""
from rest_framework import serializers

from modules.vh.models import (
    Bill,
    Booking,
    InventoryItem,
    InventoryReplenishment,
    MealBooking,
    Room,
    RoomAllotment,
    Tariff,
    VisitorCategory,
)


class VisitorCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorCategory
        fields = ["id", "code", "name", "description"]


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = [
            "id",
            "room_number",
            "room_type",
            "occupancy_type",
            "floor",
            "status",
            "created_at",
        ]


class TariffSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(source="category.code", read_only=True)

    class Meta:
        model = Tariff
        fields = [
            "id",
            "category",
            "category_code",
            "room_type",
            "occupancy_type",
            "rate_per_day",
            "effective_from",
        ]


class RoomAllotmentSerializer(serializers.ModelSerializer):
    room_number = serializers.CharField(source="room.room_number", read_only=True)
    room_type = serializers.CharField(source="room.room_type", read_only=True)

    class Meta:
        model = RoomAllotment
        fields = [
            "id",
            "booking",
            "room",
            "room_number",
            "room_type",
            "allotted_at",
            "check_in_time",
            "check_out_time",
            "is_no_show",
            "is_overstay",
        ]
        read_only_fields = ["allotted_at"]


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = [
            "id",
            "booking",
            "date",
            "meal_type",
            "add_on",
            "number_of_persons",
            "rate",
            "total_amount",
            "created_at",
        ]


class BillSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(
        source="booking.booking_reference", read_only=True
    )

    class Meta:
        model = Bill
        fields = [
            "id",
            "booking",
            "booking_reference",
            "room_charges",
            "meal_charges",
            "cancellation_charges",
            "total_amount",
            "payment_mode",
            "is_settled",
            "settled_at",
            "is_finalized",
            "guest_verification_notes",
        ]


class BookingSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(
        source="visitor_category.code", read_only=True
    )
    allotments = RoomAllotmentSerializer(many=True, read_only=True)
    bill = BillSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "booking_reference",
            "indenter_id",
            "indenter_type",
            "is_offline",
            "offline_booking_type",
            "visitor_name",
            "visitor_email",
            "visitor_phone",
            "visitor_address",
            "visitor_category",
            "category_code",
            "visit_purpose",
            "check_in_date",
            "check_out_date",
            "number_of_rooms",
            "number_of_occupants",
            "billing_responsibility",
            "status",
            "caretaker_remarks",
            "incharge_remarks",
            "cancellation_reason",
            "allotments",
            "bill",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_reference",
            "status",
            "created_at",
            "updated_at",
        ]

    def validate(self, attrs):
        check_in = attrs.get("check_in_date") or (
            self.instance and self.instance.check_in_date
        )
        check_out = attrs.get("check_out_date") or (
            self.instance and self.instance.check_out_date
        )
        if check_in and check_out and check_in > check_out:
            raise serializers.ValidationError(
                {"check_out_date": "Check-out date must be on or after check-in date."}
            )
        return attrs


class BookingActionSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    room_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class InventoryItemSerializer(serializers.ModelSerializer):
    is_below_threshold = serializers.BooleanField(read_only=True)

    class Meta:
        model = InventoryItem
        fields = [
            "id",
            "name",
            "category",
            "current_quantity",
            "minimum_threshold",
            "is_below_threshold",
            "created_at",
        ]


class InventoryReplenishmentSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = InventoryReplenishment
        fields = [
            "id",
            "item",
            "item_name",
            "quantity_requested",
            "requested_by_user_id",
            "status",
            "remarks",
            "created_at",
        ]
