from rest_framework import serializers
from modules.elm.models import (
    LeaveRequest, LeaveBalance, LeaveTransaction, HolidayCalendar, LeaveAction,
)

class LeaveActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAction
        fields = '__all__'

class LeaveTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransaction
        fields = '__all__'

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ('id', 'user_id', 'year', 'category', 'entitled_days', 'used_days', 'carried_forward_days', 'available_days')

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = '__all__'

class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveActionSerializer(many=True, read_only=True)
    transactions = LeaveTransactionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = '__all__'

class LeaveRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = ('category', 'start_date', 'end_date', 'part_of_day', 'reason', 'station_leave', 'station_destination', 'substitute_user_id')

    def validate(self, data):
        if data['start_date'] > data['end_date']:
            raise serializers.ValidationError("Start date cannot be after end date.")
        if data['station_leave'] and not data['station_destination']:
            raise serializers.ValidationError("Station destination is required when station leave is True.")
        if data['part_of_day'] in ('first_half', 'second_half') and data['start_date'] != data['end_date']:
            raise serializers.ValidationError("For part of day leave, start date and end date must be the same.")
        if data['part_of_day'] in ('first_half', 'second_half') and data['category'] != 'CL':
            raise serializers.ValidationError("For part of day leave, category must be 'CL'.")
        return data

class SubstituteResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[('accept', 'Accept'), ('decline', 'Decline')])
    note = serializers.CharField(required=False)

class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=[('recommend', 'Recommend'), ('not_recommend', 'Not Recommend'), ('approve', 'Approve'), ('reject', 'Reject')])
    note = serializers.CharField(required=False)

class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField()

class ResumptionSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    note = serializers.CharField(required=False)

class ExtensionSerializer(serializers.Serializer):
    extension_end_date = serializers.DateField()
    reason = serializers.CharField()

class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days_requested = serializers.FloatField()
    offline_reference = serializers.CharField()
    reason = serializers.CharField()