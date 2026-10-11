from rest_framework import serializers
from .models import LeaveRequest, LeaveBalance, LeaveType, LeavePolicy


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee', 'leave_type', 'start_date', 'end_date', 'purpose', 'substitute', 'status', 'created_at', 'approved_at', 'notes']
        read_only_fields = ['id', 'created_at', 'approved_at']

    def validate(self, attrs):
        # Implement validation logic here
        return attrs

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['id', 'employee', 'leave_type', 'balance', 'last_updated']
        read_only_fields = ['id', 'last_updated']

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'type', 'days_allowed', 'carry_forward', 'requires_substitute']
        read_only_fields = ['id']

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ['id', 'type', 'max_days', 'carry_forward', 'requires_substitute', 'holiday_calendar']
        read_only_fields = ['id']
