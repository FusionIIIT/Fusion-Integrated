"""Serializers for ELM.

Every write serializer uses an explicit allow-list of fields.
"""
from rest_framework import serializers

from modules.elm.models import (
    HolidayCalendar,
    LeaveBalance,
    LeaveRequest,
    LeaveTransition,
)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "user_id",
            "category",
            "year",
            "credited",
            "used",
            "carried_forward",
            "available",
        )
        read_only_fields = fields


class LeaveTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = (
            "id",
            "leave_request_id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_role",
            "reason",
            "recommendation",
            "at",
        )
        read_only_fields = fields


class LeaveRequestListSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "user_id",
            "category",
            "status",
            "request_type",
            "start_date",
            "end_date",
            "half",
            "days_counted",
            "substitute_id",
            "substitute_accepted",
            "submitted_at",
            "created_at",
        )
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    transitions = LeaveTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "user_id",
            "category",
            "status",
            "request_type",
            "start_date",
            "end_date",
            "half",
            "days_counted",
            "purpose",
            "station_leave_required",
            "station_leave_address",
            "substitute_id",
            "substitute_accepted",
            "unit_head_recommendation",
            "parent_request_id",
            "offline_sanction_reference",
            "actual_resumption_date",
            "submitted_at",
            "approved_at",
            "created_at",
            "updated_at",
            "transitions",
        )
        read_only_fields = fields


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = (
            "id",
            "date",
            "name",
            "holiday_type",
            "year",
            "is_published",
        )
        read_only_fields = fields


# -- Action Serializers (Allow-lists) -----------------------------------------

class ApplyLeaveWriteSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=4)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["full", "first_half", "second_half"], default="full")
    purpose = serializers.CharField(allow_blank=True, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    station_leave_required = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(allow_blank=True, default="")
    submit = serializers.BooleanField(default=True)


class SubstituteResponseWriteSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True, default="")


class UnitHeadReviewWriteSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    reason = serializers.CharField(allow_blank=True, default="")


class SanctionDecisionWriteSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True, default="")


class CancelRequestWriteSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, default="")


class CancelDecisionWriteSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    reason = serializers.CharField(allow_blank=True, default="")


class ExtensionRequestWriteSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(allow_blank=True, default="")


class ExtensionDecisionWriteSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    new_end_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(allow_blank=True, default="")


class ResumptionRequestWriteSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    reason = serializers.CharField(allow_blank=True, default="")


class ResumptionReviewWriteSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=True, default="")


class OfflineLeaveWriteSerializer(serializers.Serializer):
    target_user_id = serializers.IntegerField()
    category = serializers.CharField(max_length=4)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    offline_reference = serializers.CharField(max_length=200)
    purpose = serializers.CharField(allow_blank=True, default="")
    half = serializers.ChoiceField(choices=["full", "first_half", "second_half"], default="full")
