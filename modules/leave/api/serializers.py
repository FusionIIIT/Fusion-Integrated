"""Transport shapes. Models that are not the request itself are read-only."""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain import categories as cat
from modules.leave.models import (
    HolidayCalendar,
    HolidayCalendarDay,
    LeaveHierarchyStep,
    LeaveRequest,
    LeaveRequestTransition,
    SlaThreshold,
    SubstituteAssignment,
)
from modules.leave.selectors import sla as sla_selector


class LeaveRequestSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display",
                                           read_only=True)
    status_label = serializers.SerializerMethodField()
    task_class = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "kind", "category", "category_label", "start_date", "end_date",
            "half", "purpose", "status", "status_label", "task_class",
            "days_requested", "days_approved", "station_leave_required",
            "station_leave_place", "station_leave_start", "station_leave_end",
            "substitute_required", "evidence_note", "parent",
            "submitted_at", "finalised_at", "final_decision_reason",
            "unit_head_recommendation", "current_step_kind",
            "current_step_designation", "created_at",
        ]
        read_only_fields = fields

    def get_status_label(self, obj) -> str:
        return obj.status.replace("_", " ")

    def get_task_class(self, obj) -> str:
        return sla_selector.task_class_for(obj.status) or ""


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["", "first_half", "second_half"],
                                   required=False, default="")
    purpose = serializers.CharField(max_length=300)
    evidence_note = serializers.CharField(max_length=300, required=False,
                                          default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave_required = serializers.BooleanField(required=False, default=False)
    station_leave_place = serializers.CharField(max_length=120, required=False,
                                                default="")
    station_leave_start = serializers.DateField(required=False, allow_null=True)
    station_leave_end = serializers.DateField(required=False, allow_null=True)


class LeaveStatusChangeSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, default="")
    recommendation = serializers.ChoiceField(
        choices=["", "recommended", "not_recommended"], required=False, default="")


class ReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(max_length=300, required=False, default="")


class ExtensionRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=300)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, default="")


class ResumptionSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    notes = serializers.CharField(max_length=300, required=False, default="")


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    request_status = serializers.CharField(source="request.status", read_only=True)
    request_category = serializers.CharField(source="request.category",
                                             read_only=True)
    request_start = serializers.DateField(source="request.start_date", read_only=True)
    request_end = serializers.DateField(source="request.end_date", read_only=True)

    class Meta:
        model = SubstituteAssignment
        fields = ["id", "request", "request_status", "request_category",
                  "request_start", "request_end", "substitute_user_id", "state",
                  "reason", "responded_at", "created_at"]
        read_only_fields = fields


class LeaveTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestTransition
        fields = ["id", "from_status", "to_status", "event", "actor_user_id",
                  "actor_kind", "actor_designation", "recommendation", "reason",
                  "created_at"]
        read_only_fields = fields


class QueueCountSerializer(serializers.Serializer):
    waiting = serializers.IntegerField()


class LeaveWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False, default="")


class BalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    label = serializers.CharField()
    entitlement = serializers.DecimalField(max_digits=6, decimal_places=2)
    balance = serializers.DecimalField(max_digits=6, decimal_places=2)
    committed = serializers.DecimalField(max_digits=6, decimal_places=2)
    available = serializers.DecimalField(max_digits=6, decimal_places=2)


class LedgerEntrySerializer(serializers.Serializer):
    id = serializers.IntegerField()
    category = serializers.CharField()
    entry_type = serializers.CharField()
    days = serializers.DecimalField(max_digits=6, decimal_places=2)
    reference = serializers.CharField()
    reason = serializers.CharField()
    created_at = serializers.DateTimeField()


class CalendarDaySerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendarDay
        fields = ["id", "date", "kind", "name"]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    days = CalendarDaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "version", "label", "effective_from",
                  "published_at", "days"]


class CalendarDayWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=["holiday", "restricted"],
                                   required=False, default="holiday")
    name = serializers.CharField(max_length=120, required=False, default="")


class PublishCalendarSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    effective_from = serializers.DateField(required=False, allow_null=True)
    label = serializers.CharField(max_length=80, required=False, default="")
    days = CalendarDayWriteSerializer(many=True)


class HierarchyStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHierarchyStep
        fields = ["id", "sequence", "kind", "designation", "categories",
                  "is_active"]
        read_only_fields = ["id"]


class HierarchyStepWriteSerializer(serializers.Serializer):
    sequence = serializers.IntegerField(min_value=1, required=False, default=10)
    kind = serializers.ChoiceField(choices=["unit_head", "establishment",
                                           "final_authority"])
    designation = serializers.CharField(max_length=64)
    categories = serializers.ListField(child=serializers.CharField(max_length=4),
                                       required=False, default=list)


class PolicySerializer(serializers.Serializer):
    entitlements = serializers.DictField(child=serializers.IntegerField(),
                                         required=False)
    substitute_categories = serializers.ListField(
        child=serializers.CharField(max_length=4), required=False)
    max_backdate_days = serializers.IntegerField(min_value=0, required=False)
    self_sanction_designation = serializers.CharField(max_length=64, required=False)
    notes = serializers.CharField(max_length=300, required=False, default="")


class VacationPeriodSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    label = serializers.CharField(max_length=80, required=False, default="")


class SlaThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaThreshold
        fields = ["id", "task_class", "reminder_hours", "escalation_hours",
                  "escalation_designation"]
        read_only_fields = ["id"]


class SlaThresholdWriteSerializer(serializers.Serializer):
    task_class = serializers.ChoiceField(
        choices=[c for c, _ in SlaThreshold.TASK_CLASSES])
    reminder_hours = serializers.IntegerField(min_value=1)
    escalation_hours = serializers.IntegerField(min_value=1)
    escalation_designation = serializers.CharField(max_length=64, required=False,
                                                   default="")


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    days = serializers.DecimalField(max_digits=6, decimal_places=2, required=False,
                                    allow_null=True)
    sanction_reference = serializers.CharField(max_length=120)
    evidence_note = serializers.CharField(max_length=300, required=False, default="")


class BalanceAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=cat.CATEGORIES)
    year = serializers.IntegerField()
    days = serializers.DecimalField(max_digits=6, decimal_places=2)
    reason = serializers.CharField(max_length=300)
    reversal = serializers.BooleanField(required=False, default=False)
