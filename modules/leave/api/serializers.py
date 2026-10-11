from __future__ import annotations

from rest_framework import serializers
from rest_framework.fields import SerializerMethodField

from modules.leave.models import (
    Holiday,
    LeaveBalance,
    LeavePolicy,
    LeaveRequest,
    OrgUnit,
    RequestAction,
    Resumption,
)


class LeavePolicySerializer(serializers.ModelSerializer):
    """EL-UC-014, BR-EL-034"""

    class Meta:
        model = LeavePolicy
        fields = (
            "id",
            "category",
            "annual_entitlement",
            "carries_forward",
            "applies_to",
            "is_active",
        )
        read_only_fields = fields


class OrgUnitSerializer(serializers.ModelSerializer):
    """EL-UC-014, BR-EL-034"""

    class Meta:
        model = OrgUnit
        fields = ("id", "name", "unit_head_user_id")
        read_only_fields = fields


class HolidaySerializer(serializers.ModelSerializer):
    """EL-UC-015, BR-EL-034"""

    class Meta:
        model = Holiday
        fields = (
            "id",
            "date",
            "name",
            "is_restricted",
            "is_published",
        )
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """EL-UC-012, BR-EL-034"""

    available = SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "user_id",
            "year",
            "category",
            "entitled",
            "used",
            "available",
        )
        read_only_fields = fields

    def get_available(self, obj):
        return obj.entitled - obj.used


class RequestActionSerializer(serializers.ModelSerializer):
    """EL-UC-002, BR-EL-034"""

    class Meta:
        model = RequestAction
        fields = (
            "id",
            "request",
            "actor_user_id",
            "action",
            "from_status",
            "to_status",
            "note",
        )
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    """EL-UC-001, BR-EL-034"""

    actions = RequestActionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "is_half_day",
            "half_session",
            "days",
            "purpose",
            "station_leave",
            "station_address",
            "substitute_user_id",
            "substitute_status",
            "unit",
            "status",
            "recommendation",
            "decided_by_user_id",
            "decided_at",
            "decision_note",
            "is_offline",
            "actions",
        )
        read_only_fields = (
            "id",
            "user_id",
            "substitute_status",
            "status",
            "recommendation",
            "decided_by_user_id",
            "decided_at",
            "decision_note",
            "is_offline",
            "actions",
        )


class ApplySerializer(serializers.Serializer):
    """EL-UC-001, BR-EL-034"""

    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False)
    half_session = serializers.CharField(required=False, allow_blank=True)
    station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    unit_id = serializers.IntegerField(required=False, allow_null=True)
    is_faculty = serializers.BooleanField(default=False)


class SubstituteResponseSerializer(serializers.Serializer):
    """EL-UC-002, BR-EL-034"""

    accept = serializers.BooleanField()


class ReviewSerializer(serializers.Serializer):
    """EL-UC-003, BR-EL-034"""

    outcome = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    note = serializers.CharField(required=False, allow_blank=True)


class RouteSerializer(serializers.Serializer):
    """EL-UC-004, BR-EL-034"""

    note = serializers.CharField(required=False, allow_blank=True)


class SanctionSerializer(serializers.Serializer):
    """EL-UC-005, BR-EL-034"""

    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(required=False, allow_blank=True)


class ResumptionSubmitSerializer(serializers.Serializer):
    """EL-UC-011, BR-EL-034"""

    resumed_on = serializers.DateField()


class ResumptionReviewSerializer(serializers.Serializer):
    """EL-UC-011, BR-EL-034"""

    accept = serializers.BooleanField()


class PolicyWriteSerializer(serializers.Serializer):
    """EL-UC-014, BR-EL-034"""

    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    annual_entitlement = serializers.DecimalField(max_digits=5, decimal_places=1)
    carries_forward = serializers.BooleanField()
    applies_to = serializers.ChoiceField(choices=["all", "faculty", "staff"])
    is_active = serializers.BooleanField()


class UnitWriteSerializer(serializers.Serializer):
    """EL-UC-014, BR-EL-034"""

    name = serializers.CharField(max_length=120)
    unit_head_user_id = serializers.IntegerField()


class HolidayWriteSerializer(serializers.Serializer):
    """EL-UC-015, BR-EL-034"""

    date = serializers.DateField()
    name = serializers.CharField(max_length=120)
    is_restricted = serializers.BooleanField()
    is_published = serializers.BooleanField()


class OfflineRecordSerializer(serializers.Serializer):
    """EL-UC-016, BR-EL-034"""

    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = serializers.DecimalField(max_digits=5, decimal_places=1)
    note = serializers.CharField(required=False, allow_blank=True)


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resumption
        fields = (
            "id",
            "request",
            "resumed_on",
            "outcome",
            "status",
            "reviewed_by_user_id",
            "reviewed_at",
            "created_at",
        )
        read_only_fields = fields


class WithdrawSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True)
