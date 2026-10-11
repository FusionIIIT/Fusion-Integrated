from rest_framework import serializers

from modules.leave.models import (
    CalendarEntry, HolidayCalendar, LeaveApplication, LeaveLedgerEntry,
    LeavePolicy, LeaveTransition, WorkflowTask,
)


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id", "user_id", "kind", "parent", "category", "start_on", "end_on",
            "half", "purpose", "chargeable_days", "station_leave", "station_details",
            "medical_evidence", "medical_note", "status", "unit_code",
            "applicant_kind", "applicant_is_director", "requires_substitute",
            "substitute_user_id", "substitute_status", "unit_head_recommendation",
            "offline_reference", "resumption_on", "resumption_details",
            "actual_end_on", "submitted_at", "decided_at", "created_at",
        )
        read_only_fields = fields


class LeaveWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_on = serializers.DateField()
    end_on = serializers.DateField()
    purpose = serializers.CharField()
    half = serializers.ChoiceField(choices=["", "first", "second"], required=False,
                                   default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_details = serializers.CharField(required=False, allow_blank=True, default="")
    medical_evidence = serializers.BooleanField(required=False, default=False)
    medical_note = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class TransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = ("id", "frm", "to", "event", "actor_user_id", "actor_kind",
                  "note", "created_at")
        read_only_fields = fields


class LedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("id", "category", "year", "amount", "entry_type", "memo",
                  "application", "created_at")
        read_only_fields = fields


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = (
            "id", "version", "label", "published_at", "is_effective",
            "cl_annual", "rh_annual", "scl_annual", "el_staff_annual",
            "vl_faculty", "col_annual", "vl_to_el_numerator",
            "vl_to_el_denominator", "categories_requiring_substitute",
            "establishment_step_enabled", "col_requires_medical",
            "sla_reminder_hours", "sla_escalation_hours",
        )
        read_only_fields = fields


class PolicyWriteSerializer(serializers.Serializer):
    label = serializers.CharField(required=False, allow_blank=True)
    cl_annual = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    rh_annual = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    scl_annual = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    el_staff_annual = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    vl_faculty = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    col_annual = serializers.DecimalField(max_digits=6, decimal_places=2, required=False)
    categories_requiring_substitute = serializers.ListField(
        child=serializers.CharField(), required=False)
    establishment_step_enabled = serializers.BooleanField(required=False)
    col_requires_medical = serializers.BooleanField(required=False)
    sla_reminder_hours = serializers.IntegerField(required=False)
    sla_escalation_hours = serializers.IntegerField(required=False)


class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ("id", "kind", "start_on", "end_on", "label")
        read_only_fields = fields


class CalendarSerializer(serializers.ModelSerializer):
    entries = CalendarEntrySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "version", "year", "label", "published_at", "is_effective",
                  "entries")
        read_only_fields = fields


class CalendarWriteSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    label = serializers.CharField(required=False, allow_blank=True, default="")
    entries = serializers.ListField(child=serializers.DictField())


class TaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowTask
        fields = ("id", "application", "kind", "status", "assignee_user_id",
                  "assignee_role", "reminder_at", "escalate_at", "reminded_at",
                  "escalated_at", "created_at")
        read_only_fields = fields
