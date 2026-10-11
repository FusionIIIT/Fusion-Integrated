from rest_framework import serializers
from .models import LeaveBalance, LeaveApplication, SubstituteRequest, HolidayCalendar, LeavePolicy

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"

class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"

class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteRequest
        fields = "__all__"

class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"

class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"
