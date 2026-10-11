"""Input and output contracts for the ELM API."""

from decimal import Decimal

from rest_framework import serializers

from modules.elm.models import (
    ELMNotification,
    LeaveEvent,
    LeaveRequest,
    ResumptionRecord,
    WorkflowTask,
)


class LeaveEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveEvent
        fields = (
            "id",
            "from_status",
            "to_status",
            "event_type",
            "actor_user_id",
            "actor_role",
            "note",
            "data",
            "created_at",
        )


class LeaveRequestSerializer(serializers.ModelSerializer):
    category = serializers.SlugRelatedField(slug_field="code", read_only=True)
    events = LeaveEventSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "category",
            "request_type",
            "status",
            "starts_on",
            "ends_on",
            "chargeable_days",
            "half_day",
            "reason",
            "station_leave",
            "station_leave_details",
            "substitute_required",
            "substitute_user_id",
            "substitute_response",
            "evidence_reference",
            "original_leave_id",
            "route_snapshot",
            "final_decision_by_user_id",
            "decided_at",
            "offline_sanction_reference",
            "created_at",
            "updated_at",
            "events",
        )


class NewRequestSerializer(serializers.Serializer):
    category_code = serializers.ChoiceField(
        choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField()
    half_day = serializers.ChoiceField(choices=("", "first", "second"), required=False, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_required = serializers.BooleanField(required=False, default=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    evidence_reference = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, data):
        if data["ends_on"] < data["starts_on"]:
            raise serializers.ValidationError({"ends_on": "End date must not precede start date."})
        if data["half_day"] and (
            data["category_code"] != "CL" or data["starts_on"] != data["ends_on"]
        ):
            raise serializers.ValidationError(
                {"half_day": "Half-day requests are for one day of CL."}
            )
        if data["station_leave"] and not data["station_leave_details"].strip():
            raise serializers.ValidationError(
                {"station_leave_details": "Give the Station Leave details."}
            )
        return data


class ExtensionSerializer(serializers.Serializer):
    ends_on = serializers.DateField()
    reason = serializers.CharField()
    substitute_required = serializers.BooleanField(required=False, default=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField()


class SubstituteSerializer(serializers.Serializer):
    accept = serializers.BooleanField(required=False, default=False)
    replacement_user_id = serializers.IntegerField(required=False, allow_null=True)


class ReviewSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=("recommend", "not_recommended", "continue", "approve", "reject")
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionInputSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField()
    details = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionReviewSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveCategoryInputSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")])
    name = serializers.CharField(max_length=80)
    annual_entitlement = serializers.DecimalField(
        max_digits=7, decimal_places=2, min_value=Decimal("0")
    )
    employee_scope = serializers.ChoiceField(choices=("all", "faculty", "staff"))
    carry_forward = serializers.BooleanField()
    counting_rule = serializers.ChoiceField(choices=("continuous", "working_days", "calendar_days"))
    requires_medical_evidence = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class EmployeeContextInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    employee_kind = serializers.ChoiceField(choices=("faculty", "staff"))
    designation = serializers.CharField(max_length=120)
    organizational_unit = serializers.CharField(max_length=120)
    unit_head_user_id = serializers.IntegerField(required=False, allow_null=True)
    is_director = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class ApprovalRouteInputSerializer(serializers.Serializer):
    employee_kind = serializers.ChoiceField(choices=("faculty", "staff"))
    organizational_unit = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    designation = serializers.CharField(
        max_length=120, required=False, allow_blank=True, default=""
    )
    category = serializers.ChoiceField(
        choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    final_authority_user_id = serializers.IntegerField()
    final_authority_role = serializers.CharField(max_length=80)
    establishment_user_id = serializers.IntegerField(required=False, allow_null=True)
    establishment_required = serializers.BooleanField(required=False, default=False)
    is_active = serializers.BooleanField(required=False, default=True)


class CalendarInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)


class CalendarEntryInputSerializer(serializers.Serializer):
    day = serializers.DateField()
    kind = serializers.ChoiceField(choices=("closed", "restricted"))
    name = serializers.CharField(max_length=160)


class VacationInputSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    source_reference = serializers.CharField(
        max_length=240, required=False, allow_blank=True, default=""
    )


class AccountInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category_code = serializers.ChoiceField(
        choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    annual_entitlement = serializers.DecimalField(
        max_digits=7, decimal_places=2, min_value=Decimal("0")
    )
    opening_balance = serializers.DecimalField(
        max_digits=7, decimal_places=2, required=False, default=Decimal("0")
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AccountAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category_code = serializers.ChoiceField(
        choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    year = serializers.IntegerField(min_value=2000, max_value=2200)
    amount = serializers.DecimalField(max_digits=7, decimal_places=2)
    reference = serializers.CharField(max_length=240)
    note = serializers.CharField()


class OfflineInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category_code = serializers.ChoiceField(
        choices=[(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField()
    sanction_reference = serializers.CharField(max_length=240)
    evidence_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )

    def validate(self, data):
        if data["ends_on"] < data["starts_on"]:
            raise serializers.ValidationError({"ends_on": "End date must not precede start date."})
        return data


class SLAInputSerializer(serializers.Serializer):
    task_type = serializers.ChoiceField(
        choices=[
            (x, x) for x in ("substitute", "unit_head", "establishment", "final", "resumption")
        ]
    )
    reminder_after_hours = serializers.IntegerField(min_value=1)
    escalation_after_hours = serializers.IntegerField(min_value=1)
    escalation_user_id = serializers.IntegerField(required=False, allow_null=True)
    is_active = serializers.BooleanField(required=False, default=True)


class TaskSerializer(serializers.ModelSerializer):
    request_status = serializers.CharField(source="request.status", read_only=True)
    category = serializers.CharField(source="request.category.code", read_only=True)
    request_details = LeaveRequestSerializer(source="request", read_only=True)

    class Meta:
        model = WorkflowTask
        fields = (
            "id",
            "request_id",
            "task_type",
            "assigned_to_user_id",
            "status",
            "assigned_at",
            "reminder_after_hours",
            "escalation_after_hours",
            "request_status",
            "category",
            "request_details",
        )


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ResumptionRecord
        fields = (
            "id",
            "leave_id",
            "employee_user_id",
            "actual_return_date",
            "details",
            "status",
            "reviewer_user_id",
            "reviewed_at",
            "adjustment_days",
            "created_at",
        )


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = ELMNotification
        fields = ("id", "request_id", "kind", "title", "body", "payload", "created_at", "read_at")
