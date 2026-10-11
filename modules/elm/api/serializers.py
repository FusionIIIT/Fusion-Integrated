"""ELM API serializers.

Write serializers are deliberately narrow: the domain
validates everything else. Read serializers expose the
workflow state, the resolved route and the audit trail
so a reviewer sees the request exactly as the
specification's state-transition tables describe it.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.elm.domain.leave_types import (
    HALF_DAY_CHOICES,
    UNIT_TYPE_CHOICES,
)
from modules.elm.models import (
    HierarchyConfig,
    Holiday,
    HolidayCalendar,
    LeaveAccount,
    LeaveRecord,
    LeaveRequest,
    LeaveTask,
    Notification,
    OfflineLeaveRecord,
    OrgUnit,
    PolicyConfig,
    Resumption,
    SlaConfig,
    SubstituteNomination,
    VacationPeriod,
)

# -- applications ----------------------------------------------------------


class ApplicationWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_half = serializers.ChoiceField(
        choices=HALF_DAY_CHOICES, default="full")
    end_half = serializers.ChoiceField(
        choices=HALF_DAY_CHOICES, default="full")
    purpose = serializers.CharField(
        required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(
        default=False)
    station_details = serializers.JSONField(
        default=dict, required=False)
    evidence = serializers.JSONField(
        default=dict, required=False)
    submit = serializers.BooleanField(default=True)


class SubmitSerializer(serializers.Serializer):
    substitute_required = serializers.BooleanField(
        default=False)
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class WithdrawalSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class SubstituteSerializer(serializers.Serializer):
    nominee_user_id = serializers.IntegerField()
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=["approve", "reject", "recommended",
                 "not_recommended", "forward"])
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class CancellationSerializer(serializers.Serializer):
    base_request_id = serializers.IntegerField()
    effective_date = serializers.DateField(
        required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class ExtensionSerializer(serializers.Serializer):
    base_request_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    substitute_required = serializers.BooleanField(
        default=False)
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class ResumptionWriteSerializer(serializers.Serializer):
    record_id = serializers.IntegerField()
    actual_resumption_date = serializers.DateField()
    details = serializers.CharField(
        required=False, allow_blank=True, default="")


class ResumptionReviewWriteSerializer(
        serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=["normal", "early", "late"])
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(
        choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    start_half = serializers.ChoiceField(
        choices=HALF_DAY_CHOICES, default="full")
    end_half = serializers.ChoiceField(
        choices=HALF_DAY_CHOICES, default="full")
    sanction_reference = serializers.CharField()
    sanction_date = serializers.DateField()
    sanctioning_authority = serializers.CharField()
    evidence_description = serializers.CharField()
    reason_elm_unavailable = serializers.CharField()


# -- read models -------------------------------------------------------------


class SubstituteNominationSerializer(
        serializers.ModelSerializer):
    class Meta:
        model = SubstituteNomination
        fields = ["id", "nominee_user_id", "status",
                  "responded_at", "response_reason",
                  "is_active", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = ["id", "request", "task_class",
                  "assignee_user_id", "assignee_role",
                  "status", "outcome", "reason",
                  "reminder_at", "escalation_at",
                  "reminded_at", "escalated_at",
                  "escalation_detail", "completed_at",
                  "created_at"]


class LeaveRequestSerializer(
        serializers.ModelSerializer):
    tasks = TaskSerializer(many=True, read_only=True)
    substitute_nominations = (
        SubstituteNominationSerializer(
            many=True, read_only=True))

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "kind", "category", "status",
            "base_request", "user_id",
            "start_date", "end_date", "start_half",
            "end_half", "purpose", "days",
            "leave_year", "station_leave",
            "station_details", "evidence",
            "substitute_required", "route",
            "current_step", "recommendation",
            "recommendation_reason",
            "decided_by_user_id", "decided_at",
            "decision_reason", "leave_record",
            "withdrawn_at", "withdraw_reason",
            "tasks", "substitute_nominations",
            "created_at", "updated_at",
        ]


class BalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ["user_id", "leave_year", "category",
                  "opening_days", "entitled_days",
                  "used_days"]


class RecordSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = "__all__"


class TaskWithRequestSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)

    class Meta:
        model = LeaveTask
        fields = ["id", "request", "task_class",
                  "assignee_user_id", "assignee_role",
                  "status", "outcome", "reason",
                  "reminder_at", "escalation_at",
                  "reminded_at", "escalated_at",
                  "escalation_detail", "completed_at",
                  "created_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "recipient_user_id", "topic",
                  "subject", "body", "payload",
                  "status", "created_at"]


# -- configuration ------------------------------------------------------------


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyConfig
        fields = ["entitlements",
                  "director_designations",
                  "establishment_designations",
                  "year_end_month_day",
                  "station_leave_enabled",
                  "medical_evidence_required",
                  "updated_at"]


class HierarchySerializer(serializers.ModelSerializer):
    class Meta:
        model = HierarchyConfig
        fields = ["category_group", "unit_type",
                  "establishment_required",
                  "sanctioning_authority"]


class SlaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaConfig
        fields = ["task_class", "reminder_hours",
                  "escalation_hours", "escalation_action",
                  "escalation_target_role"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "date", "label", "kind",
                  "closed"]


class HolidayWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    label = serializers.CharField()
    kind = serializers.ChoiceField(
        choices=["holiday", "restricted_holiday"])
    closed = serializers.BooleanField(default=True)


class UnitHeadSerializer(serializers.Serializer):
    head_user_id = serializers.IntegerField(
        required=False, allow_null=True)


class EmployeeProfileSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    employee_kind = serializers.ChoiceField(
        choices=["faculty", "staff"])
    designation_name = serializers.CharField()
    unit_code = serializers.CharField(
        required=False, allow_null=True)


class LeaveRecordSummarySerializer(
        serializers.ModelSerializer):
    class Meta:
        model = LeaveRecord
        fields = ["id", "user_id", "leave_year",
                  "category", "start_date", "end_date",
                  "start_half", "end_half", "days",
                  "status", "station_leave",
                  "actual_end_date", "created_at"]


class CalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True,
                                     read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "year", "published_at",
                  "description", "holidays"]


class UnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ["code", "name", "unit_type",
                  "head_user_id", "projected"]


class VacationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "label", "start_date",
                  "end_date", "academic_year", "source"]


class OfflineRecordReadSerializer(
        serializers.ModelSerializer):
    class Meta:
        model = OfflineLeaveRecord
        fields = ["id", "user_id", "category",
                  "start_date", "end_date", "start_half",
                  "end_half", "days", "sanction_reference",
                  "sanction_date", "sanctioning_authority",
                  "evidence_description",
                  "reason_elm_unavailable",
                  "consistency_check",
                  "recorded_by_user_id", "leave_record",
                  "created_at"]


class RecordMaintainSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["ongoing", "completed"],
        required=False, allow_blank=True)
    actual_end_date = serializers.DateField(
        required=False, allow_null=True)
    reason = serializers.CharField(
        required=False, allow_blank=True, default="")


class YearEndSerializer(serializers.Serializer):
    leave_year = serializers.CharField(max_length=9)


class YearEndRunSerializer(serializers.Serializer):
    leave_year = serializers.CharField()
    stats = serializers.DictField()
    exceptions = serializers.ListField()


class SlaSweepReportSerializer(serializers.Serializer):
    reminded = serializers.IntegerField()
    escalated = serializers.IntegerField()


class ElmContextSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    display_name = serializers.CharField()
    employee_kind = serializers.CharField(allow_null=True)
    designation_name = serializers.CharField(allow_null=True)
    unit = serializers.DictField(allow_null=True)
    is_unit_head = serializers.BooleanField()


class BalanceDTOSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    leave_year = serializers.CharField()
    category = serializers.CharField()
    opening_days = serializers.DecimalField(
        max_digits=6, decimal_places=2)
    entitled_days = serializers.DecimalField(
        max_digits=6, decimal_places=2)
    used_days = serializers.DecimalField(
        max_digits=6, decimal_places=2)
    pending_days = serializers.DecimalField(
        max_digits=6, decimal_places=2)
    available_days = serializers.DecimalField(
        max_digits=6, decimal_places=2)


class CalendarCreateSerializer(serializers.Serializer):
    name = serializers.CharField()
    year = serializers.IntegerField()
    description = serializers.CharField(
        required=False, allow_blank=True, default="")


class UnitWriteSerializer(serializers.Serializer):
    code = serializers.SlugField(max_length=60)
    name = serializers.CharField(max_length=120)
    unit_type = serializers.ChoiceField(
        choices=UNIT_TYPE_CHOICES)


class VacationWriteSerializer(serializers.Serializer):
    label = serializers.CharField(max_length=120)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    academic_year = serializers.CharField(
        required=False, allow_blank=True, default="")


class ResumptionReadSerializer(
        serializers.ModelSerializer):
    class Meta:
        model = Resumption
        fields = ["id", "record", "request",
                  "actual_resumption_date", "details",
                  "status", "reviewed_by_user_id",
                  "reviewed_at", "adjustment_days",
                  "sync_note", "created_at"]
