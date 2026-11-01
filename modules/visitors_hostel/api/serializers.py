from rest_framework import serializers

from modules.visitors_hostel.models import (
    Bill, Booking, InventoryItem, MealBooking, ReplenishmentRequest, Room, Tariff)


class BookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Booking
        fields = ["id", "booking_number", "source", "status", "indenter_user_id",
                  "created_by_user_id",
                  "visitor_name", "visitor_email", "visitor_phone",
                  "visitor_organization", "purpose", "visitor_category",
                  "arrival_date", "departure_date", "arrival_time", "departure_time",
                  "room_count", "occupant_count", "requested_occupancy",
                  "requested_room_kind", "billing_responsibility", "department_id",
                  "project_reference", "decision_note", "cancellation_charge",
                  "created_at"]
        read_only_fields = fields


class BookingWriteSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=160)
    visitor_email = serializers.EmailField(required=False, allow_blank=True)
    visitor_phone = serializers.CharField(max_length=30)
    visitor_organization = serializers.CharField(max_length=160, required=False,
                                                  allow_blank=True)
    purpose = serializers.CharField(max_length=500)
    visitor_category = serializers.ChoiceField(choices=["A", "B", "C", "D"])
    arrival_date = serializers.DateField()
    departure_date = serializers.DateField()
    arrival_time = serializers.TimeField(required=False, allow_null=True)
    departure_time = serializers.TimeField(required=False, allow_null=True)
    room_count = serializers.IntegerField(min_value=1, max_value=30)
    occupant_count = serializers.IntegerField(min_value=1, max_value=100)
    requested_occupancy = serializers.ChoiceField(choices=["single", "double"])
    requested_room_kind = serializers.ChoiceField(choices=["suite", "non_suite"])
    billing_responsibility = serializers.ChoiceField(
        choices=["Visitor", "Indenter", "Institute", "Project"])
    department_id = serializers.IntegerField(required=False, allow_null=True)
    project_reference = serializers.CharField(max_length=80, required=False,
                                               allow_blank=True)


class ActionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["forward", "reject"], required=False)
    decision = serializers.ChoiceField(choices=["approve", "reject"], required=False)
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    confirm = serializers.BooleanField(required=False)


class AllocationSerializer(serializers.Serializer):
    room_ids = serializers.ListField(child=serializers.IntegerField(min_value=1),
                                     min_length=1, max_length=30)


class MealBookingWriteSerializer(serializers.Serializer):
    booking_id = serializers.IntegerField(min_value=1)
    meal_date = serializers.DateField()
    options = serializers.ListField(child=serializers.CharField(), min_length=1)
    add_ons = serializers.ListField(child=serializers.CharField(), required=False,
                                    allow_empty=True)
    quantity = serializers.IntegerField(min_value=1, max_value=100)


class ModificationRequestSerializer(serializers.Serializer):
    requested_changes = serializers.DictField(child=serializers.JSONField())


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = ["id", "booking_id", "meal_date", "options", "add_ons",
                  "quantity", "unit_rate"]


class InventoryItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = InventoryItem
        fields = ["id", "name", "current_quantity", "minimum_threshold", "unit", "active"]
        read_only_fields = ["id", "active"]


class InventoryChangeSerializer(serializers.Serializer):
    delta = serializers.DecimalField(max_digits=12, decimal_places=2)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


class ReplenishmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReplenishmentRequest
        fields = ["id", "item", "requested_quantity", "status", "review_note", "created_at"]
        read_only_fields = ["id", "status", "review_note", "created_at"]


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = ["id", "booking", "bill_number", "generated_at", "currency",
                  "tariff_snapshot", "line_items", "total_amount",
                  "billing_responsibility", "verified_at_checkout"]


class TariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tariff
        fields = ["id", "occupancy", "visitor_category", "daily_rate", "effective_from"]


class RoomSerializer(serializers.ModelSerializer):
    building_name = serializers.CharField(source="building.name", read_only=True)
    room_type_name = serializers.CharField(source="room_type.name", read_only=True)

    class Meta:
        model = Room
        fields = ["id", "building_name", "room_number", "room_type_name",
                  "occupancy", "status"]
