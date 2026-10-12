"""Serializers. Thin, and every write serializer is an explicit allow-list.

`fields = "__all__"` is never used here — it is exactly how `user_id`, `status`
or `days` ends up writable by whoever posts the right JSON.
"""
from rest_framework import serializers

from modules.elm.domain import enums as e
from modules.elm.models import (
    ElmSettings,
    Holiday,
    HolidayCalendar,
    LeaveAccount,
    LeaveRequest,
    LeaveTransaction,
    LeaveTypeConfig,
    ResumptionRecord,
    SlaConfig,
    SubstituteAssignment,
    VacationPeriod,
    WorkflowTask,
)


class LeaveRequestSerializer(serializers.ModelSerializer):
    applicant = serializers.IntegerField(source="user_id", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = ("id", "applicant", "kind", "category", "start_date", "end_date",
                  "half_day", "days", "purpose", "station_leave", "station_place",
                  "station_contact", "status", "substitute_user_id", "original",
                  "department", "final_decision", "decided_by_user_id",
                  "decided_at", "rejection_reason", "is_offline",
                  "sanction_reference", "created_at")
        read_only_fields = fields


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=e.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=e.HALVES, required=False,
                                       allow_blank=True, default="")
    purpose = serializers.CharField(max_length=2000, required=False,
                                    allow_blank=True, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_place = serializers.CharField(max_length=160, required=False,
                                          allow_blank=True, default="")
    station_contact = serializers.CharField(max_length=40, required=False,
                                            allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)


class DecisionSerializer(serializers.Serializer):
    decision = serializers.CharField(max_length=20)
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")


class ExtensionSerializer(serializers.Serializer):
    new_end = serializers.DateField()
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)


class NominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ResumptionSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    details = serializers.CharField(max_length=2000, required=False,
                                    allow_blank=True, default="")


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteAssignment
        fields = ("id", "request", "substitute_user_id", "responsibility_start",
                  "responsibility_end", "status", "decline_reason",
                  "responded_at", "created_at")
        read_only_fields = fields


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    reason = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                   default="")


class WorkflowTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = ("id", "request", "task_type", "role", "assigned_to_user_id",
                  "status", "decision", "acted_at", "created_at")
        read_only_fields = fields


# -- Accounts ------------------------------------------------------------------
class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ("id", "user_id", "category", "year", "balance", "used", "lapsed")
        read_only_fields = fields


class LeaveTransactionSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveTransaction
        fields = ("id", "account", "kind", "amount", "balance_after", "note",
                  "request_id", "actor_user_id", "created_at")
        read_only_fields = fields


# -- Policy --------------------------------------------------------------------
class LeaveTypeConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTypeConfig
        fields = ("id", "category", "label", "employee_kind",
                  "annual_entitlement", "carry_forward", "continuous", "half_day",
                  "requires_substitute", "requires_resumption", "allows_extension",
                  "unit_head_final", "requires_medical_evidence", "active")
        read_only_fields = ("id", "category")


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElmSettings
        fields = ("id", "current_year", "year_end_month", "year_end_day",
                  "sla_enabled")
        read_only_fields = ("id",)


# -- Calendar ------------------------------------------------------------------
class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ("id", "date", "kind", "name")
        read_only_fields = ("id",)


class HolidayCalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "name", "year", "is_published", "published_at",
                  "holidays", "created_at")
        read_only_fields = fields


class CalendarCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class HolidayWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    kind = serializers.ChoiceField(choices=Holiday.KINDS)
    name = serializers.CharField(max_length=120, required=False, allow_blank=True,
                                 default="")


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ("id", "label", "start_date", "end_date", "academic_year",
                  "created_at")
        read_only_fields = ("id", "created_at")


# -- Offline / SLA -------------------------------------------------------------
class OfflineRecordSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=e.CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=e.HALVES, required=False,
                                       allow_blank=True, default="")
    sanction_reference = serializers.CharField(max_length=160)
    purpose = serializers.CharField(max_length=2000, required=False,
                                    allow_blank=True, default="")


class ResumptionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRecord
        fields = ("id", "request", "user_id", "actual_date", "details", "status",
                  "outcome", "reviewed_at", "adjustment_note")
        read_only_fields = fields


class SlaConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaConfig
        fields = ("id", "task_type", "reminder_hours", "escalation_hours",
                  "escalate_to_designation", "change_routing", "active")
        read_only_fields = ("id", "task_type")
