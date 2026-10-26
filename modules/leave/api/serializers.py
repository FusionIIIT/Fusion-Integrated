"""Serializers for Model 2 (Qwen 14B) ELM API."""
from rest_framework import serializers

from modules.leave.models import HolidayCalendar, LeaveAccount, LeaveRequest, LeaveTransitionAudit


class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ["id", "user_id", "employee_type", "category", "year", "balance"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "title", "is_restricted_holiday", "is_published"]


class LeaveTransitionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransitionAudit
        fields = ["id", "actor_id", "action", "from_state", "to_state", "remarks", "timestamp"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    audit_logs = LeaveTransitionAuditSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "status", "chargeable_days", "unit_head_recommendation",
            "created_at", "updated_at", "audit_logs"
        ]


class CalendarEntryInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    title = serializers.CharField(max_length=200, allow_blank=False)
    is_restricted_holiday = serializers.BooleanField(default=False)


class CalendarReleaseInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120, allow_blank=False)
    entries = CalendarEntryInputSerializer(many=True, allow_empty=False)

    def validate_entries(self, entries):
        dates = [entry["date"] for entry in entries]
        if len(dates) != len(set(dates)):
            raise serializers.ValidationError("Calendar dates must be unique.")
        return entries


class OfflineSyncInputSerializer(serializers.Serializer):
    applicant_id = serializers.CharField(max_length=64, allow_blank=False)
    employee_type = serializers.ChoiceField(choices=("faculty", "staff"))
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reference_evidence = serializers.CharField(max_length=255, allow_blank=False)
    unavailable_reason = serializers.CharField(max_length=255, allow_blank=False)

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("Start date must be on or before end date.")
        return attrs


class LeaveRequestInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(allow_blank=True, required=False, default="")
    is_half_day = serializers.BooleanField(required=False, default=False)
    half_day_type = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_destination = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    station_address = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    substitute_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError("Start date must be on or before end date.")
        return attrs
