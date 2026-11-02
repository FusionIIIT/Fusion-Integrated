from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.leave_elm.models import (
    HolidayCalendar,
    HolidayDate,
    LeaveApplication,
    LeaveBalance,
    LeaveDecision,
    LeaveHierarchy,
    LeaveLedgerEntry,
    LeavePolicy,
    LeaveResumption,
    LeaveSLAConfig,
    VacationPeriod,
)


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=[x[0] for x in LeavePolicy.CATEGORIES])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day_period = serializers.ChoiceField(
        choices=[x[0] for x in LeaveApplication.HALF_DAY_PERIODS],
        required=False,
        default="full",
    )
    reason = serializers.CharField(max_length=4000)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_destination = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default="",
    )
    station_contact = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default="",
    )
    evidence_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default="",
    )
    substitute_user_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True,
    )

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "The end date must not precede the start date."},
            )
        return attrs


class LeaveDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveDecision
        fields = ("actor_user_id", "action", "note", "created_at")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    decisions = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id", "employee_id", "employee_kind", "department", "category",
            "request_type", "status", "start_date", "end_date", "actual_end_date",
            "half_day_period", "reason", "station_leave", "station_destination",
            "station_contact", "evidence_reference", "substitute_user_id",
            "substitute_accepted", "parent_application_id", "assigned_role",
            "unit_head_recommendation", "decision_note", "created_at",
            "updated_at", "decisions",
        )
        read_only_fields = fields

    @extend_schema_field(LeaveDecisionSerializer(many=True))
    def get_decisions(self, obj):
        return LeaveDecisionSerializer(obj.decisions.all(), many=True).data


class LeaveBalanceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = (
            "category", "category_label", "year", "entitlement", "carried_in",
            "converted_in", "used", "remaining", "available",
        )
        read_only_fields = fields

    @extend_schema_field(OpenApiTypes.DECIMAL)
    def get_available(self, obj):
        from modules.leave_elm.services import available_balance

        return available_balance(obj)


class LeaveLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveLedgerEntry
        fields = ("entry_type", "amount", "reference", "note", "created_at")
        read_only_fields = fields


class LeaveDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)
    recommendation = serializers.ChoiceField(
        choices=("recommended", "not_recommended"), required=False,
    )


class ExtensionSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=4000)
    evidence_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default="",
    )
    substitute_user_id = serializers.IntegerField(
        min_value=1, required=False, allow_null=True,
    )
    station_leave = serializers.BooleanField(required=False, default=False)
    station_destination = serializers.CharField(
        max_length=200, required=False, allow_blank=True, default="",
    )
    station_contact = serializers.CharField(
        max_length=80, required=False, allow_blank=True, default="",
    )


class ResumptionInputSerializer(serializers.Serializer):
    actual_resume_date = serializers.DateField()
    details = serializers.CharField(max_length=4000)


class ResumptionReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=("approve", "reject"))
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class LeaveResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveResumption
        fields = (
            "id", "application_id", "actual_resume_date", "details", "status",
            "assigned_user_id", "reviewed_by_user_id", "review_note",
            "created_at", "reviewed_at",
        )
        read_only_fields = fields


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = (
            "category", "faculty_entitlement", "staff_entitlement",
            "faculty_eligible", "staff_eligible",
            "continuous_days", "vacation_period_required", "evidence_required",
            "substitute_required", "carry_forward", "carry_forward_cap", "updated_at",
        )
        read_only_fields = ("category", "updated_at")


class LeaveHierarchySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHierarchy
        fields = (
            "id", "department", "category", "unit_head_user_id",
            "final_authority_user_id", "establishment_user_id", "updated_at",
        )
        read_only_fields = ("id", "updated_at")


class HolidayDateInputSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayDate
        fields = ("date", "is_closed", "is_restricted", "label")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    dates = HolidayDateInputSerializer(many=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "name", "year", "is_published", "published_at", "dates")
        read_only_fields = ("id", "is_published", "published_at")

    def validate_dates(self, rows):
        days = [row["date"] for row in rows]
        if len(days) != len(set(days)):
            raise serializers.ValidationError("Calendar dates must be unique.")
        return rows

    def validate(self, attrs):
        year = attrs.get("year", getattr(self.instance, "year", None))
        dates = attrs.get("dates")
        if year is not None and dates is not None and any(
            row["date"].year != year for row in dates
        ):
            raise serializers.ValidationError(
                {"dates": "Each holiday date must belong to the calendar year."},
            )
        return attrs


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ("id", "year", "start_date", "end_date", "source_reference")

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must not precede start date."},
            )
        return attrs


class LeaveSLAConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSLAConfig
        fields = (
            "id", "request_type", "reminder_after_hours",
            "escalation_after_hours", "escalation_user_id", "changes_assignment",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        reminder = attrs.get(
            "reminder_after_hours",
            getattr(self.instance, "reminder_after_hours", None),
        )
        escalation = attrs.get(
            "escalation_after_hours",
            getattr(self.instance, "escalation_after_hours", None),
        )
        if reminder is not None and escalation is not None and escalation < reminder:
            raise serializers.ValidationError(
                {"escalation_after_hours": "Escalation cannot precede reminder."},
            )
        return attrs


class OfflineLeaveSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(choices=[x[0] for x in LeavePolicy.CATEGORIES])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=4000)
    evidence_reference = serializers.CharField(max_length=500)

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError(
                {"end_date": "The end date must not precede the start date."},
            )
        return attrs


class SubstituteReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField(min_value=1)


class YearEndInputSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2200)


class LeaveYearEndConfigSerializer(serializers.Serializer):
    month = serializers.IntegerField(min_value=1, max_value=12)
    day = serializers.IntegerField(min_value=1, max_value=31)

    def validate(self, attrs):
        from datetime import date

        try:
            date(2000, attrs["month"], attrs["day"])
        except ValueError as exc:
            raise serializers.ValidationError(
                {"day": "This day is not valid for the selected month."},
            ) from exc
        return attrs
