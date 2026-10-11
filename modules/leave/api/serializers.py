"""Serializers for the leave API.

Read shapes follow the screen that consumes them rather than the table they came
from: a request carries its category label, its resolved route and its history,
because a printable, employee-accessible representation of the application is a
requirement (EL-UC-013), not a convenience.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.models import (
    HolidayCalendar,
    HolidayEntry,
    LeaveBalance,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveRecordAdjustment,
    LeaveRequest,
    LeaveRequestTransition,
    LeaveResumption,
    LeaveSubstituteAssignment,
    SlaThreshold,
    WorkflowTask,
)

HALF_CHOICES = [("", "Full day"), ("first", "First half"), ("second", "Second half")]


def _label(choices, value: str) -> str:
    return dict(choices).get(value, value)


# -- Reads ---------------------------------------------------------------------
class LeaveRequestSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    status_label = serializers.SerializerMethodField()
    kind_label = serializers.SerializerMethodField()
    is_pending = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "reference", "kind", "kind_label", "category", "category_label",
            "status", "status_label", "is_pending", "user_id",
            "period_from", "period_to", "half", "days_counted", "purpose",
            "station_leave", "substitute_user_id", "substitute_required",
            "recommendation", "recommendation_note", "decision_note",
            "decided_by_user_id", "source", "evidence_reference", "base_request",
            "route", "current_step", "applicant_is_director",
            "submitted_at", "decided_at", "withdrawn_at", "cancelled_at",
            "created_at", "updated_at",
        ]

    def get_category_label(self, obj) -> str:
        return cat.LABELS.get(obj.category, obj.category)

    def get_status_label(self, obj) -> str:
        return _label(LeaveRequest.REQUEST_STATUSES, obj.status)

    def get_kind_label(self, obj) -> str:
        return _label(LeaveRequest.KINDS, obj.kind)

    def get_is_pending(self, obj) -> bool:
        return sm.is_pending(obj.status)


class LeaveTransitionSerializer(serializers.ModelSerializer):
    actor_role_label = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequestTransition
        fields = ["id", "from_status", "to_status", "action", "actor_user_id",
                  "actor_role", "actor_role_label", "step_kind", "note", "at"]

    def get_actor_role_label(self, obj) -> str:
        return (obj.actor_role or "").replace("_", " ")


class WorkflowTaskSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    reference = serializers.CharField(source="request.reference", read_only=True)
    category = serializers.CharField(source="request.category", read_only=True)
    period_from = serializers.DateField(source="request.period_from", read_only=True)
    period_to = serializers.DateField(source="request.period_to", read_only=True)
    days_counted = serializers.DecimalField(
        source="request.days_counted", max_digits=6, decimal_places=2,
        read_only=True)

    class Meta:
        model = WorkflowTask
        fields = ["id", "request_id", "reference", "category", "period_from",
                  "period_to", "days_counted", "step_order", "step_kind",
                  "task_class", "authority", "assignee_user_id", "assignee_role",
                  "status", "status_label", "assigned_at", "reminded_at",
                  "escalated_at", "completed_at", "note"]

    def get_status_label(self, obj) -> str:
        return _label(WorkflowTask.STATUSES, obj.status)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    available_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_year", "category", "category_label",
                  "entitled_days", "carried_days", "used_days", "lapsed_days",
                  "available_days"]

    def get_category_label(self, obj) -> str:
        return cat.LABELS.get(obj.category, obj.category)

    def get_available_days(self, obj) -> str:
        return str(obj.available_days)


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ["id", "user_id", "category", "leave_year", "entry_type",
                  "days", "request_id", "note", "actor_user_id", "at"]


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    reference = serializers.CharField(source="request.reference", read_only=True)
    category = serializers.CharField(source="request.category", read_only=True)
    period_from = serializers.DateField(source="request.period_from", read_only=True)
    period_to = serializers.DateField(source="request.period_to", read_only=True)
    applicant_user_id = serializers.IntegerField(source="request.user_id",
                                                 read_only=True)

    class Meta:
        model = LeaveSubstituteAssignment
        fields = ["id", "request_id", "reference", "category", "period_from",
                  "period_to", "applicant_user_id", "nominee_user_id", "status",
                  "status_label", "responded_at", "response_note", "created_at"]

    def get_status_label(self, obj) -> str:
        return _label(LeaveSubstituteAssignment.STATUSES, obj.status)


class LeaveResumptionSerializer(serializers.ModelSerializer):
    outcome_label = serializers.SerializerMethodField()
    reference = serializers.CharField(source="request.reference", read_only=True)
    category = serializers.CharField(source="request.category", read_only=True)
    approved_to = serializers.DateField(source="request.period_to", read_only=True)

    class Meta:
        model = LeaveResumption
        fields = ["id", "request_id", "reference", "category", "user_id",
                  "actual_date", "approved_to", "remarks", "outcome",
                  "outcome_label", "submitted_at", "reviewed_at",
                  "reviewed_by_user_id", "review_note"]

    def get_outcome_label(self, obj) -> str:
        return _label(LeaveResumption.OUTCOMES, obj.outcome)


class RecordAdjustmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRecordAdjustment
        fields = ["id", "request_id", "action", "field", "before", "after",
                  "reason", "actor_user_id", "at"]


class HolidayEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayEntry
        fields = ["id", "date", "kind", "label"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    entries = HolidayEntrySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "leave_year", "label", "published_at",
                  "published_by_user_id", "is_effective", "entries"]


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ["id", "leave_year", "label", "is_current", "entitlements",
                  "continuous_counting", "half_day_categories",
                  "substitute_required_categories", "vl_to_el_ratio",
                  "year_end_month", "year_end_day", "scl_admissibility_note",
                  "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class SlaThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaThreshold
        fields = ["id", "task_class", "reminder_hours", "escalation_hours",
                  "escalation_action", "escalate_to_role", "is_active"]


# -- Writes --------------------------------------------------------------------
class ValidateLeaveSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[(c, cat.LABELS[c])
                                                for c in cat.CATEGORIES])
    period_from = serializers.DateField()
    period_to = serializers.DateField()
    half = serializers.ChoiceField(choices=HALF_CHOICES, required=False,
                                   default="")


class ApplyLeaveSerializer(ValidateLeaveSerializer):
    purpose = serializers.CharField(max_length=300, required=False, allow_blank=True)
    station_leave = serializers.JSONField(required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class WithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True)


class CancellationSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


class ExtensionSerializer(serializers.Serializer):
    period_to = serializers.DateField()
    purpose = serializers.CharField(max_length=300, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(max_length=300, required=False, allow_blank=True)


class ResumptionReviewSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


class SubstituteRespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)


class NominateReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class DecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=[
        sm.APPROVE, sm.REJECT, sm.RECOMMEND, sm.VERIFY,
        sm.APPROVE_CANCELLATION, sm.REJECT_CANCELLATION])
    note = serializers.CharField(max_length=300, required=False, allow_blank=True)
    recommendation = serializers.ChoiceField(
        choices=["recommended", "not_recommended"], required=False, default="")


class HierarchyStepSerializer(serializers.Serializer):
    step_order = serializers.IntegerField(required=False, min_value=1)
    step_kind = serializers.ChoiceField(choices=["unit_head", "establishment",
                                                 "sanction"])
    authority = serializers.CharField(max_length=32, required=False, allow_blank=True)
    unit = serializers.CharField(max_length=60, required=False, allow_blank=True)
    designation = serializers.CharField(max_length=80, required=False,
                                        allow_blank=True)
    label = serializers.CharField(max_length=80, required=False, allow_blank=True)


class HierarchyReplaceSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[("", "Any category")] + [(c, cat.LABELS[c]) for c in cat.CATEGORIES])
    steps = HierarchyStepSerializer(many=True)


class CalendarEntryWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=["closed_holiday", "restricted_holiday"])
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)


class CalendarWriteSerializer(serializers.Serializer):
    leave_year = serializers.IntegerField(min_value=2000, max_value=2100)
    label = serializers.CharField(max_length=80, required=False, allow_blank=True)
    entries = CalendarEntryWriteSerializer(many=True)


class PolicyWriteSerializer(serializers.Serializer):
    leave_year = serializers.IntegerField(min_value=2000, max_value=2100)
    label = serializers.CharField(max_length=60, required=False, allow_blank=True)
    entitlements = serializers.DictField(child=serializers.CharField(),
                                         required=False)
    continuous_counting = serializers.ListField(child=serializers.CharField(),
                                                required=False)
    half_day_categories = serializers.ListField(child=serializers.CharField(),
                                                required=False)
    year_end_month = serializers.IntegerField(min_value=1, max_value=12,
                                              required=False)
    year_end_day = serializers.IntegerField(min_value=1, max_value=31,
                                            required=False)
    scl_admissibility_note = serializers.CharField(max_length=300, required=False,
                                                   allow_blank=True)


class SlaThresholdWriteSerializer(serializers.Serializer):
    task_class = serializers.CharField(max_length=40)
    reminder_hours = serializers.IntegerField(min_value=1)
    escalation_hours = serializers.IntegerField(min_value=1)
    escalation_action = serializers.ChoiceField(
        choices=["notify", "reassign"], required=False, default="notify")
    escalate_to_role = serializers.CharField(max_length=80, required=False,
                                             allow_blank=True)


class OfflineRecordSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[(c, cat.LABELS[c])
                                                for c in cat.CATEGORIES])
    period_from = serializers.DateField()
    period_to = serializers.DateField()
    evidence_reference = serializers.CharField(max_length=160)
    purpose = serializers.CharField(max_length=300, required=False, allow_blank=True)
    certified_by = serializers.CharField(max_length=120, required=False,
                                         allow_blank=True)


class BalanceAdjustmentSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=[(c, cat.LABELS[c])
                                                for c in cat.CATEGORIES])
    leave_year = serializers.IntegerField(required=False, min_value=2000,
                                          max_value=2100)
    days = serializers.DecimalField(max_digits=6, decimal_places=2)
    note = serializers.CharField(max_length=300)


class RecordCorrectionSerializer(serializers.Serializer):
    field = serializers.ChoiceField(choices=["purpose", "evidence_reference",
                                             "station_leave", "decision_note"])
    value = serializers.CharField(max_length=400)
    reason = serializers.CharField(max_length=300)
