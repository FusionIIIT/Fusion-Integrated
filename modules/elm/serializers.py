"""Serializers for Employee Leave Management (ELM).

Handles serialization, deserialization, and payload validation for leave requests,
balance ledgers, substitute coverage, authority reviews, and holiday calendars.
"""
from __future__ import annotations

import datetime
from decimal import Decimal
from rest_framework import serializers

from .models import (
    Holiday,
    HolidayCalendar,
    LeaveActionHistory,
    LeaveBalance,
    LeaveRequest,
)


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    """Audit action history serializer."""

    class Meta:
        model = LeaveActionHistory
        fields = [
            "id",
            "actor_id",
            "action",
            "from_status",
            "to_status",
            "remarks",
            "created_at",
        ]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Multi-bucket leave balance ledger serializer (BR-EL-001..009)."""

    available = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "category",
            "year",
            "credited",
            "carried_forward",
            "converted_in",
            "availed",
            "pending",
            "converted_out",
            "available",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Complete leave request serializer with embedded audit trail and interval metadata."""

    actions = LeaveActionHistorySerializer(many=True, read_only=True)
    estimated_calendar_interval = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "half_day_type",
            "leave_days",
            "reason",
            "is_station_leave",
            "station_address",
            "station_start_date",
            "station_end_date",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "status",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_remarks",
            "estimated_calendar_interval",
            "actions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "leave_days",
            "substitute_status",
            "status",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_remarks",
            "estimated_calendar_interval",
            "created_at",
            "updated_at",
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    """Payload serializer for submitting a new leave application (EL-UC-001, BR-EL-001..015)."""

    category = serializers.ChoiceField(choices=LeaveRequest.CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(default=False)
    half_day_type = serializers.ChoiceField(
        choices=LeaveRequest.HALF_DAY_CHOICES, required=False, allow_null=True
    )
    reason = serializers.CharField(max_length=1000)

    # Station Leave Details (BR-EL-013)
    is_station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)

    # Substitute Gate (BR-EL-014, BR-EL-015)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError({"end_date": "End date cannot be earlier than start date."})

        # Half-day rule: only Casual Leave (CL) permits half-day (BR-EL-010)
        if attrs.get("half_day"):
            if attrs.get("category") != "cl":
                raise serializers.ValidationError(
                    {"half_day": "Half-day leave is only permitted for Casual Leave (CL) (BR-EL-010)."}
                )
            if start != end:
                raise serializers.ValidationError(
                    {"end_date": "Half-day leave must be on a single date (start_date must equal end_date)."}
                )
            if not attrs.get("half_day_type"):
                raise serializers.ValidationError(
                    {"half_day_type": "half_day_type ('first_half' or 'second_half') is required when half_day is True."}
                )

        # Station Leave validation (BR-EL-013)
        if attrs.get("is_station_leave") and not attrs.get("station_address", "").strip():
            raise serializers.ValidationError(
                {"station_address": "Station address is required when station leave is requested (BR-EL-013)."}
            )

        return attrs


class SubstituteResponseSerializer(serializers.Serializer):
    """Payload for substitute accept/decline action (EL-UC-002)."""

    action = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReplacementSubstituteSerializer(serializers.Serializer):
    """Payload for nominating replacement substitute after decline (EL-UC-019)."""

    substitute_id = serializers.IntegerField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadReviewSerializer(serializers.Serializer):
    """Payload for Unit Head review decision (EL-UC-003, BR-EL-016..018)."""

    decision = serializers.ChoiceField(
        choices=["approve", "reject", "recommended", "not_recommended"]
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    """Payload for Sanctioning Authority final decision (EL-UC-005, BR-EL-018, BR-EL-020)."""

    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CancellationRequestSerializer(serializers.Serializer):
    """Payload for pre-start cancellation request (EL-UC-008, BR-EL-023)."""

    remarks = serializers.CharField(required=True)


class CancellationReviewSerializer(serializers.Serializer):
    """Payload for review/sanction of cancellation request (EL-UC-005 M5)."""

    decision = serializers.ChoiceField(
        choices=["approve", "reject", "recommended", "not_recommended"]
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HolidaySerializer(serializers.ModelSerializer):
    """Institute Holiday serializer."""

    class Meta:
        model = Holiday
        fields = ["id", "date", "name", "is_rh", "is_closed"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    """Annual Holiday Calendar serializer with nested holidays."""

    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "is_published", "published_at", "published_by", "holidays"]


class YearEndRolloverSerializer(serializers.Serializer):
    """Payload for year-end VL to EL conversion and rollover (EL-UC-020)."""

    year = serializers.IntegerField()
    user_id = serializers.IntegerField(required=False)


class OfflineSanctionSerializer(serializers.Serializer):
    """Payload for recording offline sanctioned leave (EL-UC-016, BR-EL-029)."""

    applicant_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=LeaveRequest.CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    sanction_reference = serializers.CharField()
    is_faculty = serializers.BooleanField(default=False)
