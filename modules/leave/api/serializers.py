"""Request and response shapes for the leave endpoints."""
from rest_framework import serializers

from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half
from modules.leave.models import LeaveRequest, LedgerEntry

CATEGORIES = [c.value for c in Category]
HALVES = [h.value for h in Half]


class StationSerializer(serializers.Serializer):
    destination = serializers.CharField(max_length=160)
    from_date = serializers.DateField(source="from")
    to_date = serializers.DateField(source="to")


class ApplyLeaveSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    half = serializers.ChoiceField(choices=HALVES, required=False, allow_null=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station = StationSerializer(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remark = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class RemarkSerializer(serializers.Serializer):
    remark = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    remark = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class RenominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ExtensionSerializer(serializers.Serializer):
    new_end = serializers.DateField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    remark = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class ResumptionSerializer(serializers.Serializer):
    resumed_on = serializers.DateField()
    remark = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class LeaveTransitionSerializer(serializers.Serializer):
    from_state = serializers.CharField()
    to_state = serializers.CharField()
    event = serializers.CharField()
    actor_role = serializers.CharField()
    actor_user_id = serializers.IntegerField(allow_null=True)
    remark = serializers.CharField()
    workflow_ref = serializers.CharField()
    created_at = serializers.DateTimeField()


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "category", "state", "starts_on", "ends_on", "half",
            "reason", "requested_days", "actual_days", "station_leave",
            "station_destination", "resumed_on", "decided_at", "created_at",
        ]
        read_only_fields = fields


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = ["id", "year", "category", "days", "reason", "request_id", "note",
                  "created_at"]
        read_only_fields = fields


class BalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    available = serializers.DecimalField(max_digits=7, decimal_places=2)
    credited = serializers.DecimalField(max_digits=7, decimal_places=2)
    consumed = serializers.DecimalField(max_digits=7, decimal_places=2)
    restored = serializers.DecimalField(max_digits=7, decimal_places=2)


class PolicySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    version = serializers.CharField()
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(allow_null=True, required=False)
    published = serializers.BooleanField(read_only=True)
    note = serializers.CharField(allow_blank=True, required=False)
    vl_to_el_ratio = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    vl_to_el_rounding = serializers.CharField(read_only=True)
    early_return_tail = serializers.CharField(read_only=True)


class CategoryRuleSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    category = serializers.CharField()
    annual_credit = serializers.DecimalField(max_digits=6, decimal_places=2)
    carries_forward = serializers.BooleanField()
    carry_forward_cap = serializers.DecimalField(
        max_digits=6, decimal_places=2, allow_null=True
    )
    applies_to_faculty = serializers.BooleanField(allow_null=True)
    requires_evidence = serializers.BooleanField()


class CalendarSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    year = serializers.IntegerField()
    version = serializers.CharField()
    published = serializers.BooleanField(read_only=True)


class HolidaySerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    day = serializers.DateField()
    name = serializers.CharField(max_length=120)
    restricted = serializers.BooleanField(default=False)


class VacationPeriodSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(max_length=120)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORIES)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    half = serializers.ChoiceField(
        choices=HALVES, required=False, allow_null=True
    )
    faculty = serializers.BooleanField(default=False)
    unit = serializers.CharField(max_length=80, allow_blank=True, required=False)
    note = serializers.CharField(max_length=250, allow_blank=True, required=False)
