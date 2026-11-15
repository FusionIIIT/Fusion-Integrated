"""Serializers. Read serializers are read-only; write serializers are explicit
allow-lists, so `status`, `indenter_user_id` or an amount is never writable."""
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers

from modules.visitor_hostel.domain import inventory, meals
from modules.visitor_hostel.models import (
    Bill,
    BillLine,
    Booking,
    BookingTransition,
    CancellationRequest,
    DutyAssignment,
    InventoryItem,
    MealBooking,
    MealTariff,
    ModificationRequest,
    ReplenishmentRequirement,
    Room,
    RoomAllotment,
    RoomTariff,
    StayAlert,
)


# -- Read ------------------------------------------------------------------------
class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ("id", "number", "room_type", "floor", "is_active")
        read_only_fields = fields


class AllotmentSerializer(serializers.ModelSerializer):
    room = RoomSerializer(read_only=True)

    class Meta:
        model = RoomAllotment
        fields = ("id", "room", "occupancy", "allotted_at")
        read_only_fields = fields


class MealSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    class Meta:
        model = MealBooking
        fields = ("id", "meal_date", "kind", "item", "quantity", "recorded_at")
        read_only_fields = fields


class BillLineSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    class Meta:
        model = BillLine
        fields = ("kind", "description", "quantity", "unit_rate", "amount")
        read_only_fields = fields


class BillSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    lines = BillLineSerializer(many=True, read_only=True)

    class Meta:
        model = Bill
        fields = ("id", "booking", "billing_responsibility", "billing_reference",
                  "room_amount", "meal_amount", "cancellation_amount", "total",
                  "generated_at", "status", "settlement_mode", "settled_amount",
                  "receipt_reference", "settled_at", "guest_verified",
                  "verification_note", "verified_at", "lines")
        read_only_fields = fields


class CancellationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    class Meta:
        model = CancellationRequest
        fields = ("id", "requested_on", "days_before_arrival", "charge_case",
                  "charge_percent", "one_day_rent", "charge_amount", "reason",
                  "status", "confirmed_at")
        read_only_fields = fields


class ModificationSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    class Meta:
        model = ModificationRequest
        fields = ("id", "booking", "changes", "previous", "reason", "status",
                  "created_at", "confirmed_at")
        read_only_fields = fields


class BookingHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingTransition
        fields = ("from_status", "to_status", "actor_lane", "reason", "at")
        read_only_fields = fields


class StayAlertSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    visitor_name = serializers.CharField(source="booking.visitor_name", read_only=True)

    class Meta:
        model = StayAlert
        fields = ("id", "booking", "visitor_name", "kind", "expected_at", "raised_at")
        read_only_fields = fields


_BOOKING_FIELDS = (
    "id", "status", "is_offline", "source", "indenter_user_id", "visitor_name",
    "visitor_phone", "visitor_email", "visitor_organization", "visitor_address",
    "purpose", "category", "occupancy", "arrival_date", "arrival_time",
    "departure_date", "departure_time", "rooms_required", "occupants",
    "billing_responsibility", "billing_reference", "decision_reason",
    "checked_in_at", "checked_out_at", "created_at", "updated_at",
)


class BookingSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    class Meta:
        model = Booking
        fields = _BOOKING_FIELDS
        read_only_fields = fields


class BookingDetailSerializer(serializers.ModelSerializer):
    """Everything UC-VH-002 shows and prints: status, history, confirmation."""

    status = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    allotments = AllotmentSerializer(many=True, read_only=True)
    meals = MealSerializer(many=True, read_only=True)
    history = BookingHistorySerializer(source="transitions", many=True, read_only=True)
    modifications = ModificationSerializer(many=True, read_only=True)
    cancellation = serializers.SerializerMethodField()
    bill = serializers.SerializerMethodField()

    class Meta:
        model = Booking
        fields = (*_BOOKING_FIELDS, "allotments", "meals", "history",
                  "modifications", "cancellation", "bill")
        read_only_fields = fields

    def _related(self, obj, name):
        try:
            return getattr(obj, name)
        except ObjectDoesNotExist:
            return None

    def get_cancellation(self, obj) -> dict | None:
        row = self._related(obj, "cancellation")
        return CancellationSerializer(row).data if row else None

    def get_bill(self, obj) -> dict | None:
        row = self._related(obj, "bill")
        return BillSerializer(row).data if row else None


class InventoryItemSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    below_threshold = serializers.SerializerMethodField()

    class Meta:
        model = InventoryItem
        fields = ("id", "name", "kind", "unit", "quantity", "min_threshold",
                  "is_active", "below_threshold", "updated_at")
        read_only_fields = fields

    def get_below_threshold(self, obj) -> bool:
        return inventory.is_below_threshold(obj.quantity, obj.min_threshold)


class ReplenishmentSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    item = InventoryItemSerializer(read_only=True)

    class Meta:
        model = ReplenishmentRequirement
        fields = ("id", "item", "quantity_required", "note", "status", "created_at",
                  "approved_at")
        read_only_fields = fields


class RoomTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomTariff
        fields = ("id", "category", "occupancy", "rate_per_day", "effective_from")
        read_only_fields = fields


class MealTariffSerializer(serializers.ModelSerializer):
    class Meta:
        model = MealTariff
        fields = ("id", "item", "rate", "effective_from")
        read_only_fields = fields


class TariffsSerializer(serializers.Serializer):
    room = RoomTariffSerializer(many=True, read_only=True)
    meal = MealTariffSerializer(many=True, read_only=True)


class DutySerializer(serializers.ModelSerializer):
    class Meta:
        model = DutyAssignment
        fields = ("role", "user_id", "valid_from", "valid_until")
        read_only_fields = fields


# -- Write -----------------------------------------------------------------------
class RequisitionSerializer(serializers.Serializer):
    visitor_name = serializers.CharField(max_length=120)
    visitor_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    visitor_email = serializers.EmailField(required=False, allow_blank=True)
    visitor_organization = serializers.CharField(max_length=160, required=False,
                                                 allow_blank=True)
    visitor_address = serializers.CharField(max_length=300, required=False,
                                            allow_blank=True)
    purpose = serializers.CharField(max_length=1000)
    category = serializers.ChoiceField(choices=Booking.CATEGORY)
    occupancy = serializers.ChoiceField(choices=Booking.OCCUPANCY)
    arrival_date = serializers.DateField()
    arrival_time = serializers.TimeField(required=False, allow_null=True)
    departure_date = serializers.DateField()
    departure_time = serializers.TimeField(required=False, allow_null=True)
    rooms_required = serializers.IntegerField(min_value=1, max_value=50)
    occupants = serializers.IntegerField(min_value=1, max_value=200)
    billing_responsibility = serializers.ChoiceField(choices=Booking.BILLING)
    billing_reference = serializers.CharField(max_length=120, required=False,
                                              allow_blank=True)


class OfflineRequisitionSerializer(RequisitionSerializer):
    #: telephonic or walk_in; checked by the service, which owns the rule.
    source = serializers.CharField(max_length=12)
    indenter_user_id = serializers.IntegerField(required=False, allow_null=True)


class OutcomeSerializer(serializers.Serializer):
    outcome = serializers.CharField(max_length=10)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")


class AllotSerializer(serializers.Serializer):
    class _Room(serializers.Serializer):
        room_id = serializers.IntegerField()
        occupancy = serializers.ChoiceField(choices=RoomAllotment.OCCUPANCY)

    rooms = _Room(many=True, allow_empty=False)


class StayTimeSerializer(serializers.Serializer):
    at = serializers.DateTimeField(required=False, allow_null=True, default=None)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")


class ModificationWriteSerializer(serializers.Serializer):
    arrival_date = serializers.DateField(required=False)
    arrival_time = serializers.TimeField(required=False, allow_null=True)
    departure_date = serializers.DateField(required=False)
    departure_time = serializers.TimeField(required=False, allow_null=True)
    rooms_required = serializers.IntegerField(min_value=1, max_value=50, required=False)
    occupants = serializers.IntegerField(min_value=1, max_value=200, required=False)
    occupancy = serializers.ChoiceField(choices=Booking.OCCUPANCY, required=False)
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")


class MealWriteSerializer(serializers.Serializer):
    meal_date = serializers.DateField()
    #: full_day, individual or add_on; the service applies BR-VH-029/030.
    kind = serializers.CharField(max_length=10)
    item = serializers.CharField(max_length=10, required=False, allow_blank=True,
                                 default="")
    quantity = serializers.IntegerField(min_value=1, max_value=100, default=1)


class SettleSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    receipt_reference = serializers.CharField(max_length=60, required=False,
                                              allow_blank=True, default="")


class VerifySerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")


class RoomWriteSerializer(serializers.Serializer):
    number = serializers.CharField(max_length=16)
    room_type = serializers.ChoiceField(choices=Room.ROOM_TYPE)
    floor = serializers.CharField(max_length=16, required=False, allow_blank=True,
                                  default="")


class RoomActiveSerializer(serializers.Serializer):
    is_active = serializers.BooleanField()


class TariffWriteSerializer(serializers.Serializer):
    #: room or meal.
    kind = serializers.CharField(max_length=4)
    category = serializers.ChoiceField(choices=Booking.CATEGORY, required=False)
    occupancy = serializers.ChoiceField(choices=Booking.OCCUPANCY, required=False)
    item = serializers.ChoiceField(choices=meals.PRICED_ITEMS, required=False)
    rate = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0)
    effective_from = serializers.DateField()

    def validate(self, attrs):
        if attrs["kind"] not in ("room", "meal"):
            raise serializers.ValidationError("kind must be room or meal.")
        if attrs["kind"] == "room" and not (attrs.get("category") and attrs.get("occupancy")):
            raise serializers.ValidationError("A room tariff needs category and occupancy.")
        if attrs["kind"] == "meal" and not attrs.get("item"):
            raise serializers.ValidationError("A meal tariff needs an item.")
        return attrs


class InventoryWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    #: linen, utensils, consumable or other; checked by the service.
    kind = serializers.CharField(max_length=12)
    unit = serializers.CharField(max_length=20, required=False, default="pcs")
    quantity = serializers.IntegerField(min_value=0, default=0)
    min_threshold = serializers.IntegerField(min_value=0, default=0)


class AdjustSerializer(serializers.Serializer):
    delta = serializers.IntegerField()
    reason = serializers.CharField(max_length=200)


class ThresholdSerializer(serializers.Serializer):
    min_threshold = serializers.IntegerField(min_value=0)


class ReplenishmentWriteSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    quantity_required = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")
