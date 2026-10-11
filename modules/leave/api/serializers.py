from rest_framework import serializers

from modules.leave.models import (
    AuthorityRoute,
    HolidayCalendar,
    HolidayDate,
    LeaveAccountTransaction,
    LeaveApplication,
    LeaveDecision,
    LeaveNotification,
    LeavePolicy,
    LeaveRecordCorrection,
    ResumptionRecord,
    SlaConfiguration,
    SubstituteResponse,
)


class ApplicationCreateSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=4000)
    half_day_period = serializers.ChoiceField(
        choices=["", "first", "second"], required=False, allow_blank=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.CharField(required=False, allow_blank=True, max_length=500)
    medical_evidence_reference = serializers.CharField(
        required=False, allow_blank=True, max_length=500)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ApplicationReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id", "applicant_user_id", "request_kind", "original_application",
            "leave_type", "start_date", "end_date", "requested_days",
            "half_day_period", "purpose", "station_leave", "station_leave_details",
            "medical_evidence_reference", "organizational_unit", "status",
            "substitute_required", "substitute_user_id", "recommendation",
            "submitted_at", "task_assigned_at", "decided_at", "created_at",
        ]
        read_only_fields = fields


class ActionSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=[
        "accept_substitute", "decline_substitute", "replace_substitute",
        "unit_head_decision", "unit_head_cancel", "route", "sanction",
        "director_sanction", "withdraw",
    ])
    outcome = serializers.ChoiceField(
        choices=["approve", "reject", "recommended", "not_recommended", ""],
        required=False, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False)


class CancellationSerializer(serializers.Serializer):
    original_application_id = serializers.IntegerField()


class ExtensionSerializer(serializers.Serializer):
    original_application_id = serializers.IntegerField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ["leave_type", "annual_entitlement", "applies_to", "carry_forward",
                  "substitute_required", "medical_evidence_required", "higher_sanction",
                  "updated_by_user_id", "updated_at"]
        read_only_fields = ["updated_by_user_id", "updated_at", "higher_sanction"]


class AuthorityRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorityRoute
        fields = ["id", "unit_key", "leave_type", "unit_head_user_id",
                  "establishment_required", "establishment_user_id",
                  "final_authority_user_id", "updated_at"]
        read_only_fields = ["id", "updated_at"]


class HolidayDateInputSerializer(serializers.Serializer):
    date = serializers.DateField()
    name = serializers.CharField(max_length=160)
    is_restricted_holiday = serializers.BooleanField(required=False, default=False)


class CalendarCreateSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    effective_from = serializers.DateField()
    effective_to = serializers.DateField(required=False, allow_null=True)
    dates = HolidayDateInputSerializer(many=True)


class HolidayDateReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayDate
        fields = ["date", "name", "is_restricted_holiday"]


class CalendarReadSerializer(serializers.ModelSerializer):
    dates = HolidayDateReadSerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "effective_from", "effective_to", "is_published",
                  "is_current", "created_at", "dates"]


class ResumptionCreateSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    actual_resumption_date = serializers.DateField()


class ResumptionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRecord
        fields = ["id", "application_id", "employee_user_id", "actual_resumption_date",
                  "state", "reviewed_by_user_id", "synchronization_status",
                  "synchronization_error", "created_at", "reviewed_at"]
        read_only_fields = fields


class SlaSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaConfiguration
        fields = ["task_kind", "reminder_after_hours", "escalation_after_hours",
                  "escalation_user_id", "updated_at"]
        read_only_fields = ["updated_at"]


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    leave_type = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    requested_days = serializers.DecimalField(max_digits=7, decimal_places=2)
    purpose = serializers.CharField(required=False, allow_blank=True, max_length=4000)
    sanction_reference = serializers.CharField(max_length=500)


class CorrectionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    leave_type = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    amount = serializers.DecimalField(max_digits=9, decimal_places=2)
    reason = serializers.CharField(max_length=300)
    year = serializers.IntegerField(required=False)
    application_id = serializers.IntegerField(required=False, allow_null=True)
    source_key = serializers.CharField(required=False, allow_blank=True, max_length=180)


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccountTransaction
        fields = ["id", "user_id", "leave_type", "year", "amount", "transaction_type",
                  "application_id", "source_key", "note", "created_at"]
        read_only_fields = fields


class DecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveDecision
        fields = ["event", "from_status", "to_status", "actor_user_id", "actor_kind",
                  "outcome", "note", "created_at"]
        read_only_fields = fields


class SubstituteResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteResponse
        fields = ["substitute_user_id", "response", "created_at"]
        read_only_fields = fields


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = ["topic", "recipient_user_id", "status", "attempts", "last_error",
                  "sent_at", "created_at"]
        read_only_fields = fields


class CorrectionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRecordCorrection
        fields = ["id", "application_id", "user_id", "leave_type", "amount", "reason",
                  "actor_user_id", "transaction_id", "created_at"]
        read_only_fields = fields
