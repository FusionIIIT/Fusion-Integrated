"""DRF Serializers for Employee Leave Management (ELM)."""
from rest_framework import serializers

from ..models import (
    ApprovalStep,
    HolidayCalendarEntry,
    LeaveApplication,
    LeaveBalance,
    LeaveBalanceTransaction,
    LeavePolicy,
)


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = [
            "id",
            "category",
            "name",
            "annual_entitlement",
            "carry_forward",
            "counting_method",
            "applies_to",
            "requires_vacation_period",
            "requires_holiday_calendar",
            "requires_medical_evidence",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "category",
            "year",
            "entitlement",
            "balance",
            "used",
            "carried_forward",
        ]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendarEntry
        fields = [
            "id",
            "date",
            "name",
            "is_restricted_holiday",
            "year",
            "published_at",
        ]


class ApprovalApplicationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "status",
            "leave_start",
            "leave_end",
            "computed_days",
            "purpose",
            "substitute_user_id",
            "substitute_status",
        ]


class ApprovalStepSerializer(serializers.ModelSerializer):
    application = ApprovalApplicationSummarySerializer(read_only=True)

    class Meta:
        model = ApprovalStep
        fields = [
            "id",
            "application_id",
            "application",
            "step_order",
            "assigned_user_id",
            "assigned_role",
            "step_type",
            "decision",
            "comment",
            "decided_by_user_id",
            "decided_at",
        ]


class LeaveApplicationReadSerializer(serializers.ModelSerializer):
    approval_steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "status",
            "leave_start",
            "leave_end",
            "computed_days",
            "is_half_day",
            "half_day",
            "purpose",
            "station_leave_required",
            "station_leave_city",
            "station_leave_purpose",
            "substitute_user_id",
            "substitute_status",
            "substitute_noted_at",
            "is_extension",
            "extension_of_id",
            "is_cancellation",
            "cancellation_of_id",
            "is_resumption",
            "resumption_for_id",
            "actual_resumption_date",
            "is_offline_sanctioned",
            "offline_sanction_reference",
            "approval_steps",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[c[0] for c in LeavePolicy.CATEGORY])
    leave_start = serializers.DateField()
    leave_end = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    is_half_day = serializers.BooleanField(default=False)
    half_day = serializers.ChoiceField(choices=["morning", "afternoon"], required=False, allow_blank=True)
    station_leave_required = serializers.BooleanField(default=False)
    station_leave_city = serializers.CharField(max_length=200, required=False, allow_blank=True)
    station_leave_purpose = serializers.CharField(max_length=500, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    unit_head_id = serializers.IntegerField(default=2)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class ApprovalDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected", "recommended", "not_recommended"])
    comment = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ResumptionRequestSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()


class ExtensionRequestSerializer(serializers.Serializer):
    extended_end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=1000)


class OfflineSanctionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[c[0] for c in LeavePolicy.CATEGORY])
    leave_start = serializers.DateField()
    leave_end = serializers.DateField()
    reference = serializers.CharField(max_length=300)
