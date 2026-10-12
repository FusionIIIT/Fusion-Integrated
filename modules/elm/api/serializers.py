"""Serializers for the Employee Leave Management module.

Explicit allow-lists only: `fields = "__all__"` is never used here, so a
leftover column can never be written through the wire.
"""

from datetime import date

from django.utils import timezone
from rest_framework import serializers

from modules.elm.models import (
    ELMPolicy,
    HolidayCalendar,
    HolidayEntry,
    LeaveApplication,
    LeaveBalance,
    LeaveDecision,
    LeaveSubstitution,
    Resumption,
    SLAConfiguration,
    VacationPeriod,
    HierarchyLevel,
)
from modules.elm.models.roles import ELMRole, RoleGrant


# -- policy & hierarchy ------------------------------------------------------

class ELMPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = ELMPolicy
        fields = (
            "id",
            "entity_type",
            "allotment_days",
            "first_half",
            "second_half",
            "carry_forward",
            "convert_ratio",
            "counting_policy",
            "requires_substitute",
            "station_leave_supported",
            "medical_evidence_required",
            "created_at",
            "updated_at",
        )


class HierarchyLevelSerializer(serializers.ModelSerializer):
    class Meta:
        model = HierarchyLevel
        fields = (
            "id",
            "category",
            "rank",
            "role",
            "decision",
            "requires_establishment",
            "applies_to_unit",
            "created_at",
            "updated_at",
        )


# -- calendar & vacation -----------------------------------------------------

class HolidayEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayEntry
        fields = (
            "id",
            "calendar",
            "date",
            "category",
            "note",
            "created_at",
        )


class HolidayCalendarSerializer(serializers.ModelSerializer):
    entries = HolidayEntrySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = (
            "id",
            "code",
            "label",
            "start_on",
            "end_on",
            "status",
            "published_at",
            "entries",
            "created_at",
            "updated_at",
        )


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = (
            "id",
            "category",
            "label",
            "start_on",
            "end_on",
            "created_at",
            "updated_at",
        )


# -- requests & account ------------------------------------------------------

class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "applicant",
            "category",
            "balance",
            "carried_forward",
            "year",
            "created_at",
            "updated_at",
        )


class LeaveApplicationSerializer(serializers.ModelSerializer):
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "applicant",
            "category",
            "category_display",
            "reason",
            "requested_start",
            "requested_end",
            "actual_start",
            "actual_end",
            "station_leave",
            "station_leave_note",
            "substitution_required",
            "substitute_applicant_id",
            "approved_start",
            "approved_end",
            "approved_balance_deducted",
            "approval_note",
            "status",
            "current_step",
            "recipient_user_id",
            "decision",
            "year_end_applied",
            "year_end_exception",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveApplicationWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveApplication.CATEGORY)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    requested_start = serializers.DateField()
    requested_end = serializers.DateField()
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=3000
    )
    substitution_required = serializers.BooleanField(required=False, default=False)
    substitute_applicant_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveDecision
        fields = (
            "id",
            "leave_application",
            "actor_applicant_id",
            "category",
            "decision",
            "rationale",
            "requested_start",
            "requested_end",
            "created_at",
        )


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resumption
        fields = (
            "id",
            "leave_application",
            "actual_date",
            "normal",
            "early",
            "late",
            "adjustment",
            "created_at",
        )


class LeaveSubstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSubstitution
        fields = (
            "id",
            "leave_application",
            "nominated_by_applicant_id",
            "substitute_applicant_id",
            "responsibility_start",
            "responsibility_end",
            "status",
            "created_at",
            "updated_at",
        )


# -- roles -------------------------------------------------------------------

class ELMRoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = ELMRole
        fields = (
            "id",
            "name",
            "category",
            "created_at",
            "updated_at",
        )


class RoleGrantSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleGrant
        fields = (
            "id",
            "role",
            "user",
            "unit_id",
            "scope",
            "created_at",
            "updated_at",
        )


# -- SLA ---------------------------------------------------------------------

class SLAConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfiguration
        fields = (
            "id",
            "task_class",
            "reminder_hours",
            "escalation_hours",
            "escalation_mode",
            "created_at",
            "updated_at",
        )


class SLAConfigurationWriteSerializer(serializers.Serializer):
    reminder_hours = serializers.IntegerField(min_value=1, default=24)
    escalation_hours = serializers.IntegerField(min_value=1, default=72)
    escalation_mode = serializers.ChoiceField(
        choices=[("notify", "Notify only"), ("reroute", "Reroute routing/responsibility")]
    )


# -- actions (submission, consent, review, decision) -------------------------

class SubmitLeaveSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveApplication.CATEGORY)
    requested_start = serializers.DateField()
    requested_end = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_note = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=3000
    )
    substitution_required = serializers.BooleanField(required=False, default=False)
    substitute_applicant_id = serializers.IntegerField(required=False, allow_null=True)


class SubstituteConsentSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ]
    )
    rationale = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSubmissionSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    early = serializers.BooleanField(required=False, default=False)
    late = serializers.BooleanField(required=False, default=False)


class ApproveCancellationSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveApplication.CATEGORY)


class ExtensionApplySerializer(serializers.Serializer):
    additional_start = serializers.DateField()
    additional_end = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawPendingSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawRejectedSerializer(serializers.Serializer):
    pass


class AdjustYearEndSerializer(serializers.Serializer):
    adjustments = serializers.DictField(
        child=serializers.DecimalField(max_digits=6, decimal_places=2, required=False, allow_null=True),
        required=False,
        default=dict,
    )
    exception = serializers.CharField(required=False, allow_blank=True, default="")


class HolidayCalendarWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=64)
    label = serializers.CharField(max_length=120)
    start_on = serializers.DateField(allow_null=True, required=False)
    end_on = serializers.DateField(allow_null=True, required=False)
    entries = serializers.ListField(
        child=serializers.DictField(
            child=serializers.DateField(),
        ),
        required=False,
        default=list,
    )


class HolidayEntryWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    category = serializers.ChoiceField(
        choices=[("RH", "Restricted Holiday"), ("CH", "Closed Holiday")]
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class VacationPeriodWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveApplication.CATEGORY)
    label = serializers.CharField(max_length=120)
    start_on = serializers.DateField()
    end_on = serializers.DateField()


class SLAWriteSerializer(serializers.Serializer):
    reminder_hours = serializers.IntegerField(min_value=1, default=24)
    escalation_hours = serializers.IntegerField(min_value=1, default=72)
    escalation_mode = serializers.ChoiceField(
        choices=[("notify", "Notify only"), ("reroute", "Reroute routing/responsibility")]
    )


class RoleGrantWriteSerializer(serializers.Serializer):
    role = serializers.CharField(max_length=80)
    unit_id = serializers.IntegerField(required=False, allow_null=True)
    scope = serializers.DictField(required=False, default=dict)


class RoleGrantDeleteSerializer(serializers.Serializer):
    pass
