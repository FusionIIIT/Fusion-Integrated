"""DRF serializers for Employee Leave Management endpoints."""

from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.elm.domain.policy import DEFAULT_ENTITLEMENTS
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
)


class LeaveTypeInfoSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    default_entitlement = serializers.IntegerField()


class ElmLeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = (
            "id",
            "employee_id",
            "duration",
            "substitute_status",
            "status",
            "unit_head_id",
            "sanction_authority_id",
            "recommendation",
            "approver_id",
            "decision_remarks",
            "decided_at",
            "resumed_at",
            "is_offline",
            "sanction_reference",
            "original_application_id",
            "created_at",
            "updated_at",
        )


class ApplicationInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=["NONE", "FIRST", "SECOND"], required=False, default="NONE"
    )
    reason = serializers.CharField(max_length=2000, trim_whitespace=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_location = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class DecisionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            "approve",
            "reject",
            "recommend",
            "not_recommend",
            "accept_substitute",
            "decline_substitute",
            "approve_cancellation",
            "reject_cancellation",
            "review_resumption",
        ]
    )
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class ReplaceSubstituteInputSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField(min_value=1)


class ExtensionInputSerializer(serializers.Serializer):
    extended_end_date = serializers.DateField()
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=2000,
        default="Extension of ongoing leave",
        trim_whitespace=True,
    )
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_location = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class ResumptionInputSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class RolloverInputSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class OfflineLeaveInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=["NONE", "FIRST", "SECOND"], required=False, default="NONE"
    )
    reason = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default="Offline sanctioned leave"
    )
    sanction_reference = serializers.CharField(max_length=255, trim_whitespace=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_location = serializers.CharField(
        required=False, allow_blank=True, max_length=255, default=""
    )


class BalanceSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ("id", "employee_id", "category", "year", "allotted", "used", "available")

    @extend_schema_field(serializers.DecimalField(max_digits=7, decimal_places=1))
    def get_available(self, obj: LeaveBalance) -> Decimal:
        return obj.allotted - obj.used


class ProfileSerializer(serializers.ModelSerializer):
    employee_kind = serializers.ChoiceField(choices=["faculty", "staff"], source="category")

    class Meta:
        model = EmployeeLeaveProfile
        fields = (
            "id",
            "user_id",
            "employee_kind",
            "designation",
            "unit",
            "unit_head_user_id",
            "sanction_authority_user_id",
        )
        read_only_fields = ("id",)


class BalanceAllotSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=list(DEFAULT_ENTITLEMENTS))
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    allotted = serializers.DecimalField(max_digits=7, decimal_places=1, min_value=Decimal("0"))


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ("id", "date", "name", "kind", "published")


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveEvent
        fields = ("id", "actor_id", "action", "detail", "created_at")
