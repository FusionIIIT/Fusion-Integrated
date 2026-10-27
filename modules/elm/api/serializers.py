from rest_framework import serializers
from modules.elm.models import (
    LeaveRequest, LeaveBalance, LeaveSubstituteConsent, DutyResumption,
    LeaveExtension, HolidayCalendar, LeaveAction, LeaveCategory, PartOfDay, LeaveStatus
)

class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = ('id', 'actor_user_id', 'action', 'note', 'created_at')

class SubstituteConsentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSubstituteConsent
        fields = ('id', 'substitute_user_id', 'status', 'response_note', 'responded_at', 'is_current')

class DutyResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = DutyResumption
        fields = ('id', 'actual_resumption_date', 'resumption_type', 'adjustment_days', 'reason', 'status', 'reviewed_by', 'created_at')

class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)
    substitute_consents = SubstituteConsentSerializer(many=True, read_only=True)
    resumption = DutyResumptionSerializer(read_only=True)
    
    class Meta:
        model = LeaveRequest
        fields = '__all__'
        read_only_fields = ('id', 'user_id', 'computed_days', 'status', 'unit_head_recommendation', 
                            'unit_head_note', 'final_decision', 'final_decision_note', 'final_decision_by', 
                            'decision_date', 'created_at', 'updated_at')

class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ('category', 'start_date', 'end_date', 'part_of_day', 'reason', 
                  'station_leave', 'station_destination', 'substitute_user_id')

class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.DecimalField(max_digits=6, decimal_places=2, read_only=True)
    
    class Meta:
        model = LeaveBalance
        fields = ('id', 'year', 'category', 'entitled_days', 'used_days', 
                  'pending_days', 'available_days')

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ('id', 'date', 'name', 'is_rh', 'year')
