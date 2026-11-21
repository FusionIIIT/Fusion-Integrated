from rest_framework import serializers

from modules.elm.domain import leave_types as lt
from modules.elm.models import (
    HalfDay,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
    LeaveNotification,
    LeaveType,
)


class LeaveEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveEvent
        fields = ["id", "action", "from_status", "to_status", "actor_user_id", "note",
                  "created_at"]
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id", "user_id", "leave_type", "start_date", "end_date", "half_day", "days",
            "special_purpose", "special_purpose_admissible", "medical_reference",
            "station_leave", "station_address", "substitute_user_id", "status",
            "pending_action", "unit_head_recommendation", "decided_by", "decided_at",
            "decision_reason", "extends", "resumed_on", "actual_end_date", "restored_days",
            "source", "offline_reference", "created_at",
        ]
        read_only_fields = fields


class LeaveApplicationDetailSerializer(LeaveApplicationSerializer):
    events = LeaveEventSerializer(many=True, read_only=True)

    class Meta(LeaveApplicationSerializer.Meta):
        fields = [*LeaveApplicationSerializer.Meta.fields, "events"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "year", "leave_type", "entitled", "carried_in", "used",
                  "lapsed", "remaining", "closed"]
        read_only_fields = fields


class LeaveNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = ["id", "topic", "message", "application", "created_at", "read_at"]
        read_only_fields = fields


class ApplicationListSerializer(serializers.Serializer):
    results = LeaveApplicationSerializer(many=True)


class BalanceListSerializer(serializers.Serializer):
    results = LeaveBalanceSerializer(many=True)


class NotificationListSerializer(serializers.Serializer):
    results = LeaveNotificationSerializer(many=True)


class ApplyInputSerializer(serializers.Serializer):
    """The applicant never says whether SCL is admissible; the sanctioning authority does."""

    leave_type = serializers.ChoiceField(choices=LeaveType.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=HalfDay.choices, default=lt.NO_HALF)
    special_purpose = serializers.CharField(allow_blank=True, required=False, default="")
    medical_reference = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=200)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=200)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError("end_date cannot be before start_date.")
        return attrs


class OfflineInputSerializer(ApplyInputSerializer):
    user_id = serializers.IntegerField(min_value=1)
    offline_reference = serializers.CharField(max_length=120)


class ExtendInputSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    medical_reference = serializers.CharField(
        allow_blank=True, required=False, default="", max_length=200)
    special_purpose = serializers.CharField(allow_blank=True, required=False, default="")


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, required=False, default="", max_length=300)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class UnitHeadDecisionSerializer(ReasonSerializer):
    decision = serializers.ChoiceField(
        choices=["approve", "reject", "recommend", "not_recommend"])


class RouteSerializer(serializers.Serializer):
    note = serializers.CharField(allow_blank=True, required=False, default="", max_length=300)


class SanctionSerializer(ReasonSerializer):
    approve = serializers.BooleanField()
    special_purpose_admissible = serializers.BooleanField(required=False, allow_null=True,
                                                          default=None)


class ResumeSerializer(serializers.Serializer):
    resumed_on = serializers.DateField()


class VerifyResumptionSerializer(serializers.Serializer):
    verified = serializers.BooleanField(default=True)


class CalendarEntryInputSerializer(serializers.Serializer):
    kind = serializers.ChoiceField(choices=["restricted", "closed", "vacation"])
    name = serializers.CharField(max_length=255)
    date = serializers.DateField(required=False)
    start_date = serializers.DateField(required=False)
    end_date = serializers.DateField(required=False)

    def validate(self, attrs):
        if attrs["kind"] == "vacation":
            if "start_date" not in attrs or "end_date" not in attrs:
                raise serializers.ValidationError("A vacation needs start_date and end_date.")
            if attrs["end_date"] < attrs["start_date"]:
                raise serializers.ValidationError("end_date cannot be before start_date.")
        elif "date" not in attrs:
            raise serializers.ValidationError("A holiday needs a date.")
        return attrs


class CalendarSerializer(serializers.Serializer):
    restricted_holidays = serializers.ListField(child=serializers.DictField())
    closed_holidays = serializers.ListField(child=serializers.DictField())
    vacation_periods = serializers.ListField(child=serializers.DictField())


class YearEndInputSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    force = serializers.BooleanField(required=False, default=False)


class YearEndReportSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    processed = serializers.IntegerField()
    lapsed_days = serializers.DecimalField(max_digits=10, decimal_places=2)
    carried_days = serializers.DecimalField(max_digits=10, decimal_places=2)
    converted_el_days = serializers.DecimalField(max_digits=10, decimal_places=2)
    skipped_user_ids = serializers.ListField(child=serializers.IntegerField())
