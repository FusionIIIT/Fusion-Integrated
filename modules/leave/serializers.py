from rest_framework import serializers
from .models import LeaveRequest, LeaveBalance, LeaveType

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['employee_id', 'leave_type', 'balance', 'last_updated']

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee_id', 'leave_type', 'start_date', 'end_date', 'reason', 'status', 'created_at', 'updated_at']

    def validate(self, attrs):
        # Basic date validation
        if attrs['end_date'] < attrs['start_date']:
            raise serializers.ValidationError('End date must be after start date.')
        return attrs
