"""DRF Serializers for ELM module."""
from __future__ import annotations

from rest_framework import serializers

from modules.directory import contracts as directory
from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeavePolicy,
    SubstituteRequest,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "leave_type", "balance", "updated_at")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    substitute_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "applicant_name",
            "leave_type",
            "start_date",
            "end_date",
            "reason",
            "status",
            "station_leave",
            "substitute_user_id",
            "substitute_name",
            "reviewed_by_user_id",
            "review_remarks",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_applicant_name(self, obj: LeaveApplication) -> str:
        users = directory.get_users([obj.user_id])
        return users[obj.user_id].display_name if obj.user_id in users else f"User {obj.user_id}"

    def get_substitute_name(self, obj: LeaveApplication) -> str | None:
        if not obj.substitute_user_id:
            return None
        users = directory.get_users([obj.substitute_user_id])
        if obj.substitute_user_id in users:
            return users[obj.substitute_user_id].display_name
        return f"User {obj.substitute_user_id}"


class ApplyLeaveInputSerializer(serializers.Serializer):
    leave_type = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    station_leave = serializers.BooleanField(default=False, required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ReviewLeaveInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVED", "REJECTED"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseInputSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class SubstituteRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteRequest
        fields = ("id", "leave_application", "substitute_user_id", "status", "created_at")
        read_only_fields = fields


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ("id", "date", "description", "is_rh")
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "leave_type", "max_days", "description")
        read_only_fields = fields
