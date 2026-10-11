"""DRF Serializers for leave module."""
from rest_framework import serializers
from modules.leave.models import LeaveApplication, LeaveBalance, HolidayCalendar, LeaveWorkflowActionLog


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "employee_type", "category", "year", "balance"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "description", "is_restricted_holiday", "is_published"]


class LeaveWorkflowActionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveWorkflowActionLog
        fields = ["id", "actor_id", "action", "from_status", "to_status", "remarks", "created_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    logs = LeaveWorkflowActionLogSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = ["status", "chargeable_days", "unit_head_recommendation", "created_at", "updated_at"]
