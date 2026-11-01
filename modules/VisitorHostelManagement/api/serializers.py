"""DRF Serializers for Visitor Hostel Management."""
from rest_framework import serializers
from ..models import Bill, Booking, InventoryItem, MealBooking, Notification, Room, Tariff


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ["id", "room_number", "room_type", "status"]


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = ["id", "meal_date", "meal_type", "add_on", "cost"]


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = [
            "id", "room_rent", "meal_charges", "cancellation_charges", "total_amount",
            "billing_responsibility", "is_settled", "settlement_mode", "settled_at",
            "verified_by_guest", "is_immutable"
        ]


class BookingSerializer(serializers.ModelSerializer):
    rooms = RoomSerializer(many=True, read_only=True)
    meals = MealBookingSerializer(many=True, read_only=True)
    bill = BillSerializer(read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id", "indenter_id", "visitor_name", "visitor_email", "visitor_phone",
            "visitor_category", "purpose", "check_in_date", "check_out_date",
            "number_of_rooms", "number_of_occupants", "billing_responsibility",
            "is_offline", "status", "caretaker_remarks", "incharge_remarks",
            "cancellation_reason", "cancellation_charge", "actual_check_in",
            "actual_check_out", "rooms", "meals", "bill", "created_at"
        ]


class BookingCreateSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=120)
    visitor_email = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")
    visitor_phone = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    visitor_category = serializers.CharField(max_length=10, default="A")
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    check_in_date = serializers.DateField()
    check_out_date = serializers.DateField()
    number_of_rooms = serializers.IntegerField(default=1)
    number_of_occupants = serializers.IntegerField(default=1)
    billing_responsibility = serializers.ChoiceField(choices=["visitor", "indenter", "institute", "project"], default="visitor")
    is_offline = serializers.BooleanField(default=False)


class ReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["reject", "forward"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CancelSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AllotSerializer(serializers.Serializer):
    room_ids = serializers.ListField(child=serializers.IntegerField())


class MealCreateSerializer(serializers.Serializer):
    meal_date = serializers.DateField()
    meal_type = serializers.ChoiceField(choices=["breakfast", "lunch", "dinner", "full_day"])
    add_on = serializers.ChoiceField(choices=["none", "tea", "milk"], default="none")


class InventorySerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "item_name", "category", "quantity", "min_threshold", "replenishment_requested", "replenishment_approved", "replenishment_qty"]


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ["id", "category", "room_type", "rate_per_day", "effective_from"]


class RoleReassignSerializer(serializers.Serializer):
    role = serializers.ChoiceField(choices=["caretaker", "incharge"])
    new_user_id = serializers.IntegerField()


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "recipient_email", "recipient_user_id", "event_type", "subject", "message", "created_at"]
