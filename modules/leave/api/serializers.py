"""Serializers for Leave module."""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.models import LeaveBalance, LeaveRequest, LeaveTransition


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "category",
            "allocated",
            "used",
            "pending",
            "available",
        ]


class LeaveTransitionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = ["from_status", "to_status", "actor_user_id", "reason", "at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    transitions = LeaveTransitionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "half_day_period",
            "days_count",
            "purpose",
            "station_leave",
            "station_details",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "unit_head_remarks",
            "authority_remarks",
            "rejection_reason",
            "status",
            "created_at",
            "updated_at",
            "transitions",
        ]


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveRequest.CATEGORY)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=LeaveRequest.HALF_DAY_PERIOD, default="none"
    )
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(default=False)
    station_details = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class SubstituteActionSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveTransitionSerializer(serializers.Serializer):
    to_status = serializers.ChoiceField(choices=LeaveRequest.STATUS)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
