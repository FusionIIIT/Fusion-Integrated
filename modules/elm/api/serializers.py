from rest_framework import serializers
from modules.elm.models import LeaveRequest, LeaveBalance, LeaveActionLog


class LeaveActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionLog
        fields = ["id", "actor_user_id", "actor_role", "action", "remarks", "created_at"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    balance = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_type", "year", "credited", "availed", "pending", "balance"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    action_logs = LeaveActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "applicant_user_id", "leave_type", "start_date", "end_date",
            "duration_days", "is_half_day", "half_day_session", "reason",
            "station_leave", "station_leave_address", "out_of_station_from", "out_of_station_to",
            "substitute_user_id", "substitute_status", "substitute_remarks",
            "status", "current_approver_role", "rejection_reason", "created_at", "updated_at",
            "action_logs"
        ]
        read_only_fields = ["id", "status", "current_approver_role", "substitute_status", "created_at", "updated_at"]


class LeaveCreateSerializer(serializers.Serializer):
    leave_type = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_days = serializers.DecimalField(max_digits=4, decimal_places=1)
    reason = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_session = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(required=False, allow_blank=True, default="")
    out_of_station_from = serializers.DateField(required=False, allow_null=True)
    out_of_station_to = serializers.DateField(required=False, allow_null=True)
    substitute_id = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteDecisionSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ApproverDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
    forward_higher = serializers.BooleanField(default=False)
