# Serializers for ELM API endpoints
from rest_framework import serializers

from modules.leave.domain.constants import (
    ALL_HALF_DAYS,
    ALL_LEAVE_TYPES,
    HALF_DAY_NONE,
)
from modules.leave.models import LeaveApplication, LeaveBalance


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Serializer for employee leave balance and remaining days."""

    available = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        read_only=True,
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "year",
            "allocated",
            "used",
            "available",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    """Serializer for viewing leave applications."""

    user_id = serializers.ReadOnlyField()
    days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)
    status = serializers.ReadOnlyField()
    reviewed_by = serializers.ReadOnlyField()
    review_remarks = serializers.ReadOnlyField()
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day",
            "days",
            "reason",
            "is_station_leave",
            "station_leave_address",
            "replacement_user_id",
            "status",
            "reviewed_by",
            "review_remarks",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    """Serializer for submitting a new leave application."""

    leave_type = serializers.ChoiceField(choices=[(lt, lt) for lt in ALL_LEAVE_TYPES])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=[(hd, hd) for hd in ALL_HALF_DAYS],
        default=HALF_DAY_NONE,
        required=False,
    )
    reason = serializers.CharField(min_length=3)
    is_station_leave = serializers.BooleanField(default=False, required=False)
    station_leave_address = serializers.CharField(
        required=False,
        allow_blank=True,
        default="",
    )
    replacement_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        default=None,
    )

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be prior to start date."}
            )
        if attrs.get("is_station_leave") and not attrs.get("station_leave_address", "").strip():
            raise serializers.ValidationError(
                {"station_leave_address": "Station leave address is required for station leave."}
            )
        return attrs


class LeaveReviewSerializer(serializers.Serializer):
    """Serializer for reviewing (approve/reject) a leave application."""

    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
