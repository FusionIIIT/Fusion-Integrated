"""Wire shapes for ELM."""
from rest_framework import serializers

from modules.leave.models import (
    LEAVE_TYPES,
    LeaveApplication,
    LeaveBalance,
    RestrictedHoliday,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.DecimalField(max_digits=6, decimal_places=1,
                                         read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "year", "leave_type", "entitled", "carried_forward",
                  "availed", "available"]


class LeaveApprovalSerializer(serializers.Serializer):
    step_role = serializers.CharField()
    action = serializers.CharField()
    actor_user_id = serializers.IntegerField(allow_null=True)
    note = serializers.CharField(allow_blank=True)
    at = serializers.DateTimeField()


class LeaveApplicationSerializer(serializers.ModelSerializer):
    approvals = LeaveApprovalSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["id", "user_id", "kind", "parent", "leave_type", "start_date",
                  "end_date", "half_day", "days", "reason", "station_leave",
                  "station_place", "substitute_user_id", "substitute_status",
                  "status", "pending_role", "unit_head_recommendation",
                  "authority_chain", "actual_end_date", "decision_note",
                  "decided_at", "created_at", "approvals"]


class ApplyLeaveSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=[c for c, _ in LEAVE_TYPES])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=["", "first", "second"],
                                       required=False, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_place = serializers.CharField(required=False, allow_blank=True,
                                          default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    action = serializers.CharField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class NominationResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSerializer(serializers.Serializer):
    actual_end_date = serializers.DateField()
    note = serializers.CharField(required=False, allow_blank=True, default="")


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestrictedHoliday
        fields = ["id", "year", "on_date", "name", "is_closed_holiday",
                  "is_published"]
