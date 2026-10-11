"""Serializers for Employee Leave Management endpoints."""
from rest_framework import serializers

from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            "id",
            "code",
            "name",
            "annual_quota",
            "can_carry_forward",
            "requires_substitute",
            "is_active",
        )
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    remaining = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "leave_type",
            "year",
            "allocated",
            "used",
            "pending",
            "remaining",
        )
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    total_days = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day",
            "station_leave",
            "station_address",
            "reason",
            "substitute_user_id",
            "substitute_status",
            "status",
            "reviewer_user_id",
            "review_remarks",
            "decided_at",
            "total_days",
            "created_at",
        )
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type_code = serializers.CharField(max_length=16)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(required=False, default=False)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=("recommended", "approved", "rejected")
    )
    remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class SubstituteDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=("accepted", "declined"))


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ("id", "date", "title", "is_restricted")
        read_only_fields = fields
