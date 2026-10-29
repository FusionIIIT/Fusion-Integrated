"""Serializers: shaped to the screens, not to the tables.

Write serializers take exactly the fields a form owns. A serializer that
accepted `status` or `user_id` from the client would let an applicant approve
their own request.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    ApprovalTask,
    CancellationRequest,
    ExtensionRequest,
    HierarchyRoute,
    HierarchyRouteStep,
    Holiday,
    HolidayCalendar,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRequest,
    NotificationOutbox,
    OrganizationalUnit,
    ResumptionRequest,
    SlaThreshold,
    SubstituteNomination,
    VacationPeriod,
)
from modules.leave.models.requests import NOMINATION_STATUSES, TASK_KINDS


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ("id", "date", "name", "is_restricted_holiday")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "year", "status", "is_effective", "published_at", "holidays")


class HolidayWriteSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1970, max_value=2999)
    date = serializers.DateField()
    name = serializers.CharField(max_length=120)
    is_restricted_holiday = serializers.BooleanField(default=False)


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ("id", "label", "start_date", "end_date", "year",
                  "source_reference")


class OrganizationalUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ("id", "name", "head_user_id", "is_active")


class HierarchyRouteStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = HierarchyRouteStep
        fields = ("id", "kind", "order", "designation", "user_id")


class HierarchyRouteSerializer(serializers.ModelSerializer):
    steps = HierarchyRouteStepSerializer(many=True, read_only=True)

    class Meta:
        model = HierarchyRoute
        fields = ("id", "name", "leave_category", "org_unit", "is_active", "steps")


class SlaThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaThreshold
        fields = ("id", "task_kind", "reminder_hours", "escalate_hours",
                  "escalation_user_id", "escalation_designation",
                  "escalation_changes_routing", "is_active")


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "casual_days", "restricted_holiday_days",
                  "special_casual_days", "earned_days", "vacation_days",
                  "commuted_days", "vacation_to_earned_ratio",
                  "earned_carries_forward", "commuted_carries_forward",
                  "earned_carry_forward_cap", "commuted_carry_forward_cap",
                  "year_end_month", "substitute_required_for",
                  "establishment_step_enabled", "category_kinds",
                  "created_at", "updated_at")
        read_only_fields = ("id", "created_at", "updated_at")


class SubstituteNominationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteNomination
        fields = ("id", "leave_request", "extension_request_id", "nominee_user_id",
                  "status", "period_start", "period_end", "responded_at",
                  "created_at")


class ApprovalTaskSerializer(serializers.ModelSerializer):
    leave_request_id = serializers.IntegerField(read_only=True)
    status_label = serializers.SerializerMethodField()

    class Meta:
        model = ApprovalTask
        fields = ("id", "leave_request_id", "subject_type", "subject_id", "kind",
                  "assignee_user_id", "status", "status_label", "assigned_at",
                  "completed_at", "reminder_due_at", "escalation_due_at",
                  "reminder_sent_at", "escalated_at", "escalated_to_user_id",
                  "outcome", "note")

    def get_status_label(self, obj) -> str:
        return obj.status.replace("_", " ").title()


class LeaveRequestSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    half_day_allowed = serializers.SerializerMethodField()
    org_unit_name = serializers.CharField(source="org_unit.name", read_only=True,
                                          default="")

    class Meta:
        model = LeaveRequest
        fields = ("id", "status", "status_label", "category", "category_label",
                  "start_date", "end_date", "requested_days", "half_day", "half",
                  "half_day_allowed", "purpose", "station_leave_required",
                  "station_leave_details", "substitute_required", "kind",
                  "department", "org_unit", "org_unit_name",
                  "unit_head_recommendation", "medical_evidence_reference",
                  "offline_sanction_reference", "source", "decided_by_user_id",
                  "decided_at", "decision_note", "created_at", "updated_at")
        read_only_fields = ("id", "status", "status_label", "requested_days",
                            "substitute_required", "unit_head_recommendation",
                            "decided_by_user_id", "decided_at", "decision_note",
                            "created_at", "updated_at")

    def get_category_label(self, obj) -> str:
        return cat.LABELS.get(obj.category, obj.category)

    def get_status_label(self, obj) -> str:
        return obj.status.replace("_", " ").title()

    def get_half_day_allowed(self, obj) -> bool:
        return obj.category == cat.CASUAL


class LeaveRequestWriteSerializer(serializers.Serializer):
    """Only what a form owns. Status, days and identity are the server's."""
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=500)
    half_day = serializers.BooleanField(default=False)
    half = serializers.ChoiceField(choices=cat.HALVES, required=False, allow_blank=True)
    station_leave_required = serializers.BooleanField(default=False)
    station_leave_details = serializers.CharField(
        max_length=500, required=False, allow_blank=True)
    medical_evidence_reference = serializers.CharField(
        max_length=300, required=False, allow_blank=True)

    def validate(self, attrs) -> dict:
        if attrs.get("half_day") and attrs["start_date"] != attrs["end_date"]:
            raise serializers.ValidationError(
                {"half_day": "A half day applies to a single date."})
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "The last date cannot be before the first date."})
        return attrs


class SubmitSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class DecisionSerializer(serializers.Serializer):
    """One shape for every decision edge. `approve` is required so a decision is
    never recorded by omission."""
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    recommendation = serializers.ChoiceField(
        choices=("", "recommended", "not_recommended"), required=False,
        allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class NominateSerializer(serializers.Serializer):
    nominee_user_id = serializers.IntegerField()
    extension_request_id = serializers.IntegerField(required=False, allow_null=True)


class NominationResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class ExtensionRequestWriteSerializer(serializers.Serializer):
    additional_start_date = serializers.DateField()
    additional_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)

    def validate(self, attrs) -> dict:
        if attrs["additional_start_date"] > attrs["additional_end_date"]:
            raise serializers.ValidationError(
                {"additional_end_date": "The last date cannot be before the "
                                        "first date."})
        return attrs


class ResumptionWriteSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    details = serializers.CharField(max_length=500, required=False, allow_blank=True)


class CancellationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = CancellationRequest
        fields = ("id", "leave_request", "status", "reason",
                  "unit_head_recommendation", "decided_by_user_id", "decided_at",
                  "decision_note", "created_at")


class ExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtensionRequest
        fields = ("id", "leave_request", "status", "additional_start_date",
                  "additional_end_date", "additional_days", "reason",
                  "substitute_required", "unit_head_recommendation",
                  "decided_by_user_id", "decided_at", "decision_note",
                  "created_at")


class ResumptionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRequest
        fields = ("id", "leave_request", "status", "actual_resumption_date",
                  "details", "adjustment_days", "reviewed_by_user_id",
                  "reviewed_at", "review_note", "created_at")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("user_id", "year", "category", "days", "year_end_applied")


class LeaveLedgerEntrySerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    signed_days = serializers.DecimalField(max_digits=8, decimal_places=2,
                                           read_only=True)

    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "user_id", "year", "category", "category_label", "kind",
                  "days", "signed_days", "note", "leave_request_id",
                  "created_by_user_id", "created_at")

    def get_category_label(self, obj) -> str:
        return cat.LABELS.get(obj.category, obj.category)


class BalanceAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=1970, max_value=2999)
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    days = serializers.DecimalField(max_digits=8, decimal_places=2)
    kind = serializers.ChoiceField(choices=("credit", "debit", "adjustment"),
                                   default="adjustment")
    note = serializers.CharField(max_length=300)


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanction_reference = serializers.CharField(max_length=300)
    purpose = serializers.CharField(max_length=500, required=False, allow_blank=True)


class RouteWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    leave_category = serializers.ChoiceField(choices=cat.CATEGORIES,
                                             required=False, allow_blank=True)
    org_unit_id = serializers.IntegerField(required=False, allow_null=True)
    steps = serializers.ListField(child=serializers.DictField(), allow_empty=False)


class UnitWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    head_user_id = serializers.IntegerField(required=False, allow_null=True)


class ThresholdWriteSerializer(serializers.Serializer):
    task_kind = serializers.ChoiceField(choices=TASK_KINDS)
    reminder_hours = serializers.IntegerField(required=False, allow_null=True,
                                              min_value=1)
    escalate_hours = serializers.IntegerField(required=False, allow_null=True,
                                              min_value=1)
    escalation_user_id = serializers.IntegerField(required=False, allow_null=True)
    escalation_designation = serializers.CharField(
        max_length=120, required=False, allow_blank=True)
    escalation_changes_routing = serializers.BooleanField(default=False)


class YearEndRunSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=1970, max_value=2999)
    dry_run = serializers.BooleanField(default=False)
    only_user_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, allow_empty=False)


class ReconciliationSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=1970, max_value=2999)


class NotificationOutboxSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationOutbox
        fields = ("id", "topic", "status", "subject", "recipient_user_id",
                  "recipient_email", "sent_at", "attempts", "last_error",
                  "created_at")


class NominationStatusFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=NOMINATION_STATUSES, required=False)


class StateFilterSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=sm.LEAVE_STATES, required=False)
    category = serializers.ChoiceField(choices=cat.CATEGORIES, required=False)
    year = serializers.IntegerField(required=False)