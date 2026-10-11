"""Serializers for Model 2 (Qwen 14B) ELM API."""
from rest_framework import serializers
from modules.leave.models import LeaveRequest, LeaveAccount, HolidayCalendar, LeaveTransitionAudit


class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ["id", "user_id", "employee_type", "category", "year", "balance"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "title", "is_restricted_holiday", "is_published"]


class LeaveTransitionAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransitionAudit
        fields = ["id", "actor_id", "action", "from_state", "to_state", "remarks", "timestamp"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    audit_logs = LeaveTransitionAuditSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = [
            "status", "chargeable_days", "unit_head_recommendation",
            "created_at", "updated_at", "audit_logs"
        ]
