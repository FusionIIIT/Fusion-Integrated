"""DRF serializers for Employee Leave Management endpoints."""

from decimal import Decimal

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.elm.domain.policy import DEFAULT_ENTITLEMENTS
from modules.elm.models import (
    EmployeeLeaveProfile,
    Holiday,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveBalance,
    LeaveEvent,
    LeaveNotification,
    SlaConfig,
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
            "establishment_id",
            "sanction_authority_id",
            "recommendation",
            "approver_id",
            "decision_remarks",
            "decided_at",
            "actual_resumption_date",
            "resumption_remarks",
            "resumed_at",
            "is_offline",
            "sanction_reference",
            "extended_from",
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
    medical_evidence = serializers.CharField(
        required=False, allow_blank=True, max_length=2000, default=""
    )
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
            "verify_and_route",
            "forward_to_sanction",
            "approve_cancellation",
            "reject_cancellation",
            "recommend_cancellation",
            "not_recommend_cancellation",
        ]
    )
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


class ReplacementSubstituteInputSerializer(serializers.Serializer):
    replacement_substitute_user_id = serializers.IntegerField(min_value=1)


class ExtensionInputSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class ResumptionInputSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000, default="")


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
    sanction_reference = serializers.CharField(max_length=255)


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
            "establishment_user_id",
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


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = (
            "id",
            "recipient_id",
            "application_id",
            "topic",
            "message",
            "is_reminder",
            "is_escalation",
            "read",
            "created_at",
        )


class LeaveAccountTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccountTransaction
        fields = (
            "id",
            "employee_id",
            "year",
            "category",
            "transaction_type",
            "amount",
            "balance_after",
            "reference",
            "created_at",
        )


class SlaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaConfig
        fields = ("id", "task_type", "reminder_hours", "escalation_hours", "escalate_to_user_id")


class PrintableApplicationSerializer(serializers.Serializer):
    application = ElmLeaveApplicationSerializer()
    profile = ProfileSerializer()
    events = EventSerializer(many=True)
    printable_text = serializers.CharField()


class YearEndInputSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100, required=False)


class YearEndOutputSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    lapsed_records = serializers.IntegerField()
    vl_converted_faculty = serializers.IntegerField()
    carried_forward = serializers.IntegerField()
    exceptions = serializers.ListField(child=serializers.CharField(), required=False)


class SlaProcessOutputSerializer(serializers.Serializer):
    reminded = serializers.IntegerField()
    escalated = serializers.IntegerField()
