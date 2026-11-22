from decimal import Decimal

from django.utils import timezone
from rest_framework import serializers

from .models import (
    AuditEvent,
    Bill,
    BookingRequest,
    InventoryItem,
    InventoryReplenishment,
    MealBooking,
    Room,
    RoomAllotment,
    VisitorCategoryTariff,
)


class VisitorCategoryTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = VisitorCategoryTariff
        fields = "__all__"
        extra_kwargs = {"daily_rate": {"min_value": Decimal("0")}}


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = "__all__"


class MealBookingSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealBooking
        fields = "__all__"
        read_only_fields = ("booking",)
        extra_kwargs = {"rate": {"min_value": Decimal("0")}, "quantity": {"min_value": 1}}


class RoomAllotmentSerializer(serializers.ModelSerializer):
    room_details = RoomSerializer(source="room", read_only=True)

    class Meta:
        model = RoomAllotment
        fields = "__all__"


class BillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bill
        fields = "__all__"


class BookingRequestSerializer(serializers.ModelSerializer):
    allotments = RoomAllotmentSerializer(many=True, read_only=True)
    meal_bookings = MealBookingSerializer(many=True, read_only=True)
    bill = BillSerializer(read_only=True)

    class Meta:
        model = BookingRequest
        fields = "__all__"
        read_only_fields = (
            "indenter_id",
            "legacy_indenter_id",
            "status",
            "is_offline",
            "rejection_reason",
            "cancellation_requested_at",
            "cancellation_reason",
            "modification_request",
        )
        extra_kwargs = {
            "number_of_rooms": {"min_value": 1, "max_value": 100},
            "number_of_occupants": {"min_value": 1},
        }

    def validate(self, attrs):
        def value(name, default=None):
            return attrs.get(name, getattr(self.instance, name, default))

        start, end = value("check_in_date"), value("check_out_date")
        from datetime import time

        if (
            start
            and end
            and (end, value("check_out_time", time(11)))
            <= (start, value("check_in_time", time(14)))
        ):
            raise serializers.ValidationError("Departure must be after arrival.")
        if self.instance is None and start and start < timezone.localdate():
            raise serializers.ValidationError({"check_in_date": "Arrival cannot be in the past."})
        capacity = value("number_of_rooms", 1) * (
            2 if value("occupancy", "single") == "double" else 1
        )
        if value("number_of_occupants", 1) > capacity:
            raise serializers.ValidationError("Occupant count exceeds requested room capacity.")
        return attrs


class InventoryItemSerializer(serializers.ModelSerializer):
    below_threshold = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = "__all__"
        extra_kwargs = {"quantity": {"min_value": 0}, "minimum_threshold": {"min_value": 0}}

    def get_below_threshold(self, obj) -> bool:
        return obj.is_below_threshold()


class InventoryReplenishmentSerializer(serializers.ModelSerializer):
    item_name = serializers.CharField(source="item.name", read_only=True)

    class Meta:
        model = InventoryReplenishment
        fields = "__all__"
        read_only_fields = ("status",)
        extra_kwargs = {"requested_quantity": {"min_value": 1}}


class RouteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["forward", "reject"])
    reason = serializers.CharField(required=False, default="", allow_blank=True, max_length=2000)

    def validate(self, attrs):
        if attrs["action"] == "reject" and not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "A rejection reason is required."})
        return attrs


class DecisionSerializer(RouteSerializer):
    action = None
    decision = serializers.ChoiceField(choices=["approve", "reject"])

    def validate(self, attrs):
        if attrs["decision"] == "reject" and not attrs["reason"].strip():
            raise serializers.ValidationError({"reason": "A rejection reason is required."})
        return attrs


class AllotmentInputSerializer(serializers.Serializer):
    room_ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1), allow_empty=False, max_length=100
    )


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class SettlementSerializer(serializers.Serializer):
    receipt_number = serializers.CharField(max_length=100)
    guest_verified = serializers.BooleanField()

    def validate_guest_verified(self, value):
        if not value:
            raise serializers.ValidationError("Record guest verification before settlement.")
        return value


class StatusSerializer(serializers.Serializer):
    status = serializers.CharField()


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ("action", "actor_id", "created_at", "details")


class HostelReportSerializer(serializers.Serializer):
    booking_summary = serializers.ListField(child=serializers.DictField())
    category_occupancy = serializers.ListField(child=serializers.DictField())
    billing_summary = serializers.DictField()
    inventory_usage = serializers.ListField(child=serializers.DictField())
    daily_occupancy = serializers.ListField(child=serializers.DictField())
    arrivals = serializers.ListField(child=serializers.DictField())
    departures = serializers.ListField(child=serializers.DictField())
    pending_approvals = serializers.IntegerField()
    alerts = serializers.ListField(child=serializers.DictField())
