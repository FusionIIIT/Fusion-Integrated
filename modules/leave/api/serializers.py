from rest_framework import serializers
from modules.leave.models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "max_days_per_year", "requires_attachment", "is_active"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining_days = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_type", "leave_type_code", "leave_type_name", "year", "allocated_days", "used_days", "remaining_days"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "leave_type", "leave_type_code", "leave_type_name",
            "start_date", "end_date", "duration_days", "reason", "status",
            "approver_user_id", "rejection_reason", "approved_at", "created_at"
        ]
        read_only_fields = ["id", "user_id", "status", "approver_user_id", "approved_at", "created_at"]

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date must be on or after start date."})
        return attrs


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True)
