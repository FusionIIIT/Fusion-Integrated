from rest_framework import serializers
from ..models.leave import EmployeeLeave, LeaveBalance, StationLeaveDetail

class StationLeaveSerializer(serializers.ModelSerializer):
    class Meta:
        model = StationLeaveDetail
        fields = ['destination', 'departure_datetime', 'return_datetime', 'emergency_contact', 'address_during_leave']

class EmployeeLeaveSerializer(serializers.ModelSerializer):
    station_leave = StationLeaveSerializer(source='station_leave_detail', required=False)
    applicant_name = serializers.CharField(source='applicant.get_full_name', read_only=True)

    class Meta:
        model = EmployeeLeave
        fields = ['id', 'applicant', 'applicant_name', 'leave_type', 'start_date', 'end_date', 'duration_days', 'is_half_day', 'half_day_slot', 'purpose', 'status', 'applied_on', 'unit_head_remarks', 'station_leave']
        read_only_fields = ['applicant', 'status', 'applied_on']

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ['leave_type', 'credited', 'consumed', 'available', 'year']
