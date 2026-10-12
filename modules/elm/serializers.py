from rest_framework import serializers
from .models import LeaveType, EmployeeLeave, LeaveRequest, LeaveApproval

class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ['id', 'name', 'description']

class EmployeeLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeLeave
        fields = ['id', 'user', 'start_date', 'end_date', 'reason', 'status']

class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    class Meta:
        model = LeaveRequest
        fields = ['id', 'employee', 'leave_type', 'request_date', 'approved_by']

class LeaveApprovalSerializer(serializers.ModelSerializer):
    leave_request = LeaveRequestSerializer(read_only=True)
    class Meta:
        model = LeaveApproval
        fields = ['id', 'leave_request', 'approved_by', 'approval_date']