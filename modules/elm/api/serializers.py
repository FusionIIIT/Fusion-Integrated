from rest_framework import serializers
from modules.elm.models import LeaveType, LeaveRequest, LeaveBalance, SubstituteResponse

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name']

class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ['id', 'leave_type', 'user_id', 'start_date', 'end_date', 'reason']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['id', 'leave_type', 'user_id', 'balance']

class SubstituteResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteResponse
        fields = ['id', 'leave_request', 'substitute_user_id', 'response_date', 'status']
