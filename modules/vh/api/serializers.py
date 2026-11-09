"""Serializers for the Visitors Hostel (VH) API."""
from rest_framework import serializers

from modules.vh.models import (
    Bill,
    Booking,
    BookingModification,
    BookingStatus,
    InventoryCategory,
    InventoryItem,
    InventoryReplenishment,
    MealAddOn,
    MealBooking,
    MealType,
    ModificationStatus,
    Room,
    RoomAllotment,
    Tariff,
    VHAlert,
    VHNotificationLog,
    VisitorCategory,
    VHMSUserRole,
    VHMSUserRoleType,
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

    def validate(self, attrs):
        booking = attrs.get("booking") or (self.instance and self.instance.booking)
        meal_date = attrs.get("date") or (self.instance and self.instance.date)

        if booking:
            # BR-VH-025: Meal bookings shall be recorded only for guests staying in VH
            if booking.status != BookingStatus.CHECKED_IN:
                raise serializers.ValidationError(
                    {"booking": "Meal bookings can only be recorded for guests currently staying in VH (CHECKED_IN status) per BR-VH-025."}
                )

            # BR-VH-031: A meal booking shall be linked to the guest's recorded stay duration
            if meal_date and (meal_date < booking.check_in_date or meal_date > booking.check_out_date):
                raise serializers.ValidationError(
                    {"date": f"Meal date {meal_date} must be within the guest stay duration ({booking.check_in_date} to {booking.check_out_date}) per BR-VH-031."}
                )

        return attrs


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

    def validate(self, attrs):
        # BR-VH-037: Maintain immutable billing records for audit
        if self.instance and self.instance.is_finalized:
            # Check if any financial or status fields are being altered
            restricted_fields = ["room_charges", "meal_charges", "cancellation_charges", "total_amount", "is_finalized"]
            for f in restricted_fields:
                if f in attrs and attrs[f] != getattr(self.instance, f):
                    raise serializers.ValidationError(
                        f"Cannot modify '{f}' on a finalized bill; bills are immutable for audit per BR-VH-037."
                    )
        return attrs


class BookingModificationSerializer(serializers.ModelSerializer):
    booking_reference = serializers.CharField(source="booking.booking_reference", read_only=True)

    class Meta:
        model = BookingModification
        fields = [
            "id",
            "booking",
            "booking_reference",
            "requested_by_user_id",
            "new_check_in_date",
            "new_check_out_date",
            "new_number_of_rooms",
            "new_number_of_occupants",
            "reason",
            "status",
            "confirmed_by_user_id",
            "remarks",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "requested_by_user_id",
            "status",
            "confirmed_by_user_id",
            "created_at",
        ]

    def validate(self, attrs):
        booking = attrs.get("booking") or (self.instance and self.instance.booking)
        if booking:
            terminal_statuses = (
                BookingStatus.CHECKED_IN,
                BookingStatus.CHECKED_OUT,
                BookingStatus.CANCELLED,
            )
            if booking.status in terminal_statuses:
                raise serializers.ValidationError(
                    {"booking": f"Cannot modify booking in '{booking.status}' status; modifications apply pre-arrival."}
                )
        return attrs


class BookingSerializer(serializers.ModelSerializer):
    category_code = serializers.CharField(
        source="visitor_category.code", read_only=True
    )
    allotments = RoomAllotmentSerializer(many=True, read_only=True)
    bill = BillSerializer(read_only=True)
    modifications = BookingModificationSerializer(many=True, read_only=True)

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
            "assigned_caretaker_id",
            "assigned_incharge_id",
            "caretaker_remarks",
            "incharge_remarks",
            "cancellation_reason",
            "calculated_cancellation_charge",
            "allotments",
            "bill",
            "modifications",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "booking_reference",
            "status",
            "assigned_caretaker_id",
            "assigned_incharge_id",
            "calculated_cancellation_charge",
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


class VHMSUserRoleSerializer(serializers.ModelSerializer):
    role_display = serializers.CharField(source="get_role_type_display", read_only=True)

    class Meta:
        model = VHMSUserRole
        fields = [
            "id",
            "role_type",
            "role_display",
            "user_id",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
        ]


class VHAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = VHAlert
        fields = [
            "id",
            "alert_type",
            "booking",
            "inventory_item",
            "message",
            "recipient_role",
            "recipient_user_id",
            "is_resolved",
            "resolved_at",
            "created_at",
        ]


class VHNotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = VHNotificationLog
        fields = [
            "id",
            "event_type",
            "booking",
            "recipient_email",
            "recipient_user_id",
            "subject",
            "body",
            "created_at",
        ]
