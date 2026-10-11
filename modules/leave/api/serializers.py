"""DRF serializers for Leave module."""
from rest_framework import serializers

from modules.leave.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id", "code", "name", "description", "annual_quota",
            "max_carry_forward", "allow_half_day", "requires_doc_after_days",
            "is_active",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining = serializers.DecimalField(max_digits=6, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_type", "leave_type_code", "leave_type_name",
                  "year", "credited", "used", "remaining"]
        read_only_fields = ["id", "remaining"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "leave_type", "leave_type_code", "leave_type_name",
            "start_date", "end_date", "half_day", "days_requested",
            "reason", "status", "applied_at", "approved_by_user_id",
            "decided_at", "decision_note",
        ]
        read_only_fields = ["id", "days_requested", "status", "applied_at",
                            "approved_by_user_id", "decided_at", "decision_note"]


class ApplyLeaveSerializer(serializers.Serializer):
    leave_type_id = serializers.IntegerField()
    start_date    = serializers.DateField()
    end_date      = serializers.DateField()
    half_day      = serializers.ChoiceField(choices=["morning", "afternoon"], required=False, allow_null=True)
    reason        = serializers.CharField(max_length=1000, required=False, default="")


class TransitionLeaveSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=["approved", "rejected", "cancelled", "revoked"])
    reason    = serializers.CharField(max_length=300, required=False, default="")
