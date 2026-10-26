from rest_framework import serializers

from .models import (
    AuthorityRoute,
    CalendarDay,
    LeaveBalance,
    LeaveEvent,
    LeavePolicy,
    LeaveRequest,
    LeaveType,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = ("id",)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"
        read_only_fields = ("id", "last_updated")

    def validate_balance(self, value):
        if value < 0:
            raise serializers.ValidationError("Balance cannot be negative.")
        return value


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"
        read_only_fields = ("id",)

    def validate(self, attrs):
        reminder_hours = attrs.get("reminder_hours")
        escalation_hours = attrs.get("escalation_hours")

        if self.instance:
            if reminder_hours is None:
                reminder_hours = self.instance.reminder_hours
            if escalation_hours is None:
                escalation_hours = self.instance.escalation_hours
        else:
            if reminder_hours is None:
                reminder_hours = 24
            if escalation_hours is None:
                escalation_hours = 48

        if reminder_hours <= 0:
            raise serializers.ValidationError(
                "Escalation must exceed a positive reminder threshold"
            )
        if escalation_hours <= reminder_hours:
            raise serializers.ValidationError(
                "Escalation must exceed a positive reminder threshold"
            )

        attrs["reminder_hours"] = reminder_hours
        attrs["escalation_hours"] = escalation_hours
        return attrs


class LeaveRequestSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee",
            "leave_type",
            "start_date",
            "end_date",
            "purpose",
            "substitute",
            "employee_kind",
            "unit",
            "half_day",
            "station_leave",
            "station_details",
            "medical_evidence",
            "days",
            "substitute_status",
            "route",
            "step",
            "operation",
            "base_request",
            "actual_return_date",
            "status",
            "approved_at",
            "updated_at",
            "created_at",
            "notes",
            "events",
        ]
        read_only_fields = (
            "id",
            "employee",
            "employee_kind",
            "unit",
            "days",
            "substitute_status",
            "route",
            "step",
            "operation",
            "base_request",
            "actual_return_date",
            "status",
            "approved_at",
            "updated_at",
            "created_at",
            "notes",
            "events",
        )

    def get_events(self, obj) -> list[dict]:
        events = obj.events.all()
        return LeaveEventSerializer(events, many=True).data


class AuthorityRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorityRoute
        fields = "__all__"
        read_only_fields = ("id",)

    def validate_higher_authorities(self, value):
        if not isinstance(value, list) or not all(isinstance(item, int) for item in value):
            raise serializers.ValidationError("higher_authorities must be a list of integers.")
        if not all(item > 0 for item in value):
            raise serializers.ValidationError("All higher_authorities must be positive integers.")
        if len(set(value)) != len(value):
            raise serializers.ValidationError("All higher_authorities must be distinct.")
        return value


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarDay
        fields = "__all__"
        read_only_fields = ("id", "date", "kind", "published", "source")

    def validate_kind(self, value):
        if value == "VACATION":
            raise serializers.ValidationError(
                "Cannot create or update CalendarDay with kind 'VACATION' via ELM API."
            )
        return value


class LeaveEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveEvent
        fields = "__all__"
        read_only_fields = (
            "id",
            "request",
            "employee",
            "actor",
            "action",
            "delta",
            "details",
            "created_at",
        )
