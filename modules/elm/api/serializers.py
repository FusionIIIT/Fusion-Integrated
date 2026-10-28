from rest_framework import serializers

from modules.elm.models import (
    LEAVE_CATEGORIES,
    ApprovalRoute,
    EmployeeProfile,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    OrgUnit,
    RequestEvent,
    VacationPeriod,
    WorkflowTask,
)


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LEAVE_CATEGORIES)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    purpose = serializers.CharField()
    half_day_part = serializers.ChoiceField(
        choices=("", "first_half", "second_half"), required=False, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="")
    station_contact = serializers.CharField(required=False, allow_blank=True, default="")
    medical_evidence = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveFollowUpSerializer(serializers.Serializer):
    purpose = serializers.CharField()


class OfflineLeaveSerializer(serializers.Serializer):
    applicant_user_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=LEAVE_CATEGORIES)
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    purpose = serializers.CharField()
    offline_reference = serializers.CharField(max_length=160)
    offline_reason = serializers.CharField()
    offline_sanctioned_on = serializers.DateField()


class LeaveRecordMaintenanceSerializer(serializers.Serializer):
    reason = serializers.CharField()
    purpose = serializers.CharField(required=False)
    station_leave = serializers.BooleanField(required=False)
    station_destination = serializers.CharField(required=False, allow_blank=True)
    station_contact = serializers.CharField(required=False, allow_blank=True)
    medical_evidence = serializers.CharField(required=False, allow_blank=True)
    offline_reference = serializers.CharField(
        required=False, max_length=160, allow_blank=True)
    offline_reason = serializers.CharField(required=False)
    offline_sanctioned_on = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        changes = {key: value for key, value in attrs.items() if key != "reason"}
        if not changes:
            raise serializers.ValidationError(
                "At least one permitted record field must be provided.")
        return attrs


class ExtensionSerializer(LeaveFollowUpSerializer):
    ends_on = serializers.DateField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ResumptionSerializer(LeaveFollowUpSerializer):
    actual_resume_date = serializers.DateField()


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class ReplaceSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class TaskDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=("approve", "reject", "recommend", "not_recommend"))
    note = serializers.CharField(required=False, allow_blank=True, default="")


class WorkflowTaskSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = WorkflowTask
        fields = (
            "id", "sequence", "role", "assigned_user_id", "is_final", "status",
            "assigned_at", "acted_at", "decision_note",
        )


class RequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ("actor_user_id", "event", "from_status", "to_status", "note", "created_at")


class LeaveRequestSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    tasks = WorkflowTaskSerializer(many=True, read_only=True)
    events = RequestEventSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id", "applicant_user_id", "category", "request_type", "status",
            "starts_on", "ends_on", "half_day_part", "requested_days", "purpose",
            "station_leave", "station_destination", "station_contact",
            "medical_evidence", "substitute_user_id", "substitute_response",
            "parent_id", "actual_resume_date", "offline_reference", "submitted_at",
            "decided_at", "decision_note", "tasks", "events",
        )
        read_only_fields = fields


class WorkflowTaskQueueSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)
    request = LeaveRequestSerializer(read_only=True)

    class Meta:
        model = WorkflowTask
        fields = ("id", "sequence", "role", "is_final", "status", "assigned_at", "request")


class LeavePolicySerializer(serializers.ModelSerializer):
    escalation_user_id = serializers.IntegerField(
        min_value=1, allow_null=True, required=False)

    class Meta:
        model = LeavePolicy
        fields = (
            "id", "year", "casual_days", "restricted_holiday_days",
            "special_casual_days", "earned_days", "commuted_days",
            "vacation_days", "reminder_after_hours", "escalate_after_hours",
            "escalation_user_id",
        )

    def validate(self, attrs):
        day_fields = (
            "casual_days", "restricted_holiday_days", "special_casual_days",
            "earned_days", "commuted_days", "vacation_days",
        )
        for field in day_fields:
            if field in attrs and attrs[field] < 0:
                raise serializers.ValidationError({field: "Entitlement cannot be negative."})
        reminder = attrs.get(
            "reminder_after_hours",
            getattr(self.instance, "reminder_after_hours", 0))
        escalation = attrs.get(
            "escalate_after_hours",
            getattr(self.instance, "escalate_after_hours", 0))
        if reminder <= 0 or escalation <= 0:
            raise serializers.ValidationError(
                "SLA reminder and escalation thresholds must be positive.")
        if escalation <= reminder:
            raise serializers.ValidationError(
                "The escalation threshold must be later than the reminder threshold.")
        return attrs


class ApprovalRouteSerializer(serializers.ModelSerializer):
    unit_id = serializers.PrimaryKeyRelatedField(
        source="unit", queryset=OrgUnit.objects.filter(is_active=True),
        allow_null=True, required=False)

    class Meta:
        model = ApprovalRoute
        fields = ("id", "category", "unit_id", "designation", "steps", "is_active")

    def validate_steps(self, steps):
        if not isinstance(steps, list) or not steps:
            raise serializers.ValidationError("At least one sanctioning step is required.")
        for step in steps:
            if (not isinstance(step, dict)
                    or type(step.get("user_id")) is not int
                    or step["user_id"] <= 0
                    or not isinstance(step.get("role"), str)
                    or not step["role"].strip()):
                raise serializers.ValidationError(
                    "Each step needs an integer user_id and a non-empty role.")
        return steps


class HolidayCalendarSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "year", "name", "status", "published_at",
                  "published_by_user_id")
        read_only_fields = ("status", "published_at", "published_by_user_id")


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ("id", "calendar", "date", "name", "kind")
        read_only_fields = ("calendar",)


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ("id", "academic_year", "label", "starts_on", "ends_on", "source")

    def validate(self, attrs):
        starts_on = attrs.get("starts_on", getattr(self.instance, "starts_on", None))
        ends_on = attrs.get("ends_on", getattr(self.instance, "ends_on", None))
        if starts_on and ends_on and ends_on < starts_on:
            raise serializers.ValidationError(
                {"ends_on": "The end date must be on or after the start date."})
        return attrs


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrgUnit
        fields = ("id", "code", "name", "unit_head_user_id", "is_active")


class EmployeeProfileUpdateSerializer(serializers.ModelSerializer):
    unit_id = serializers.PrimaryKeyRelatedField(
        source="unit", queryset=OrgUnit.objects.filter(is_active=True))

    class Meta:
        model = EmployeeProfile
        fields = (
            "employee_kind", "unit_id", "designation", "requires_substitute",
            "is_director", "is_active",
        )


class LeaveBalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    year = serializers.IntegerField()
    entitlement = serializers.DecimalField(max_digits=8, decimal_places=2)
    carry_forward = serializers.DecimalField(max_digits=8, decimal_places=2)
    used = serializers.DecimalField(max_digits=8, decimal_places=2)
    balance = serializers.DecimalField(max_digits=8, decimal_places=2)


class YearEndResultSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    processed_accounts = serializers.IntegerField()
    completed_at = serializers.DateTimeField()


class EmployeeProfileSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    employee_kind = serializers.CharField()
    unit_id = serializers.IntegerField(allow_null=True)
    designation = serializers.CharField()
    requires_substitute = serializers.BooleanField()
    is_director = serializers.BooleanField()
    is_active = serializers.BooleanField()


class StatusCountSerializer(serializers.Serializer):
    status = serializers.CharField()
    count = serializers.IntegerField()


class CategoryCountSerializer(serializers.Serializer):
    category = serializers.CharField()
    count = serializers.IntegerField()


class LeaveReportSummarySerializer(serializers.Serializer):
    requests_by_status = StatusCountSerializer(many=True)
    requests_by_category = CategoryCountSerializer(many=True)


class ModuleHealthSerializer(serializers.Serializer):
    module = serializers.CharField()
    status = serializers.CharField()
