from rest_framework import serializers
from modules.leave_elm.models import LeaveApplication, LeaveBalance, SubstituteResponse
from typing import Dict

class LeaveBalanceSerializer(serializers.Serializer):
    """Serializer for LeaveBalance object."""
    available_balance = serializers.DecimalField(max_digits=5, decimal_places=1)
    annual_entitlement = serializers.DecimalField(max_digits=5, decimal_places=1)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """Serializer for LeaveApplication object."""
    
    # Custom field to display category nicely
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    
    class Meta:
        model = LeaveApplication
        fields = ['id', 'employee_id', 'category', 'category_display', 'start_date', 'end_date', 'reason', 'is_station_leave', 'duration_days', 'status', 'substitute_id']
        read_only_fields = ['status', 'duration_days']

class SubstituteResponseSerializer(serializers.ModelSerializer):
    """Serializer for SubstituteResponse object."""
    
    class Meta:
        model = SubstituteResponse
        fields = ['id', 'application_id', 'substitute_id', 'response_status', 'notes']

class LeaveApplicationCreateSerializer(serializers.Serializer):
    """Input serializer for creating a new leave application."""
    employee_id = serializers.CharField(max_length=64)
    category = serializers.CharField(max_length=2)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)
    substitute_id = serializers.CharField(max_length=64, required=False)
    is_station_leave = serializers.BooleanField(default=False)

class LeaveApplicationUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating application status (e.g., approval/rejection)."""
    notes = serializers.CharField(max_length=500, required=False)
    
    class Meta:
        model = LeaveApplication
        fields = ['status', 'notes']
        read_only_fields = ['id']