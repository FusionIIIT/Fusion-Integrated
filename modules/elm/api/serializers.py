from rest_framework import serializers

from modules.elm.models import (
    LeaveApplication,
    LeaveCalendar,
    LeaveCalendarDate,
    LeaveHierarchy,
    LeavePolicy,
    VacationPeriod,
)


class LeaveApplicationInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[
            ("CL", "CL"),
            ("RH", "RH"),
            ("SCL", "SCL"),
            ("EL", "EL"),
            ("COL", "COL"),
            ("VL", "VL"),
        ]
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    cl_half = serializers.ChoiceField(
        choices=[("none", "Full day"), ("first", "First half"), ("second", "Second half")],
        required=False,
        default="none",
    )
    purpose = serializers.CharField(max_length=1000)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_leave_details = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )
    requires_substitute = serializers.BooleanField(required=False, default=False)
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=2147483647
    )
    evidence_reference = serializers.CharField(
        max_length=240, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError({"end_date": "End date must not precede start date."})
        if attrs.get("station_leave") and not attrs.get("station_leave_details", "").strip():
            raise serializers.ValidationError(
                {"station_leave_details": "Explain the Station Leave requirement."}
            )
        if attrs.get("cl_half") != "none" and (
            attrs["category"] != "CL" or attrs["start_date"] != attrs["end_date"]
        ):
            raise serializers.ValidationError(
                {"cl_half": "Half-day selection is valid only for one-date CL."}
            )
        if attrs.get("requires_substitute") and not attrs.get("substitute_user_id"):
            raise serializers.ValidationError(
                {"substitute_user_id": "Select an eligible substitute."}
            )
        return attrs


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "applicant_user_id",
            "employee_kind",
            "department",
            "request_type",
            "parent_application",
            "category",
            "start_date",
            "end_date",
            "cl_half",
            "requested_days",
            "purpose",
            "station_leave",
            "station_leave_details",
            "requires_substitute",
            "substitute_user_id",
            "substitute_response",
            "status",
            "current_assignee_user_id",
            "unit_head_recommendation",
            "final_decision",
            "final_decision_note",
            "action_reason",
            "actual_resumption_date",
            "evidence_reference",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=[
            ("approve", "Approve"),
            ("reject", "Reject"),
            ("recommended", "Recommended"),
            ("not_recommended", "Not recommended"),
            ("route", "Route"),
            ("review", "Review"),
        ]
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=[("accept", "Accept"), ("decline", "Decline")])


class RetryAfterDeclineSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        min_value=1,
        max_value=2147483647,
    )


class ActionReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class ExtensionSerializer(ActionReasonSerializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True, min_value=1, max_value=2147483647
    )

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError({"end_date": "End date must not precede start date."})
        return attrs


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    details = serializers.CharField(max_length=1000, required=False, allow_blank=True, default="")


class OfflineLeaveRecordSerializer(serializers.Serializer):
    applicant_user_id = serializers.IntegerField(min_value=1, max_value=2147483647)
    employee_kind = serializers.ChoiceField(choices=[("faculty", "Faculty"), ("staff", "Staff")])
    category = serializers.ChoiceField(
        choices=[(c, c) for c in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=1000)
    evidence_reference = serializers.CharField(max_length=240)
    department = serializers.CharField(max_length=120, required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["end_date"] < attrs["start_date"]:
            raise serializers.ValidationError({"end_date": "End date must not precede start date."})
        if not attrs["evidence_reference"].strip():
            raise serializers.ValidationError(
                {"evidence_reference": "Evidence reference must not be blank."}
            )
        return attrs


class LeavePolicySerializer(serializers.ModelSerializer):
    def validate_annual_entitlement(self, value):
        if value < 0:
            raise serializers.ValidationError("Annual entitlement cannot be negative.")
        return value

    class Meta:
        model = LeavePolicy
        fields = (
            "id",
            "category",
            "annual_entitlement",
            "employee_scope",
            "carry_forward",
            "continuous_counting",
            "medical_evidence_required",
            "enabled",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "category", "created_at", "updated_at")


class LeaveCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendar
        fields = (
            "id",
            "name",
            "year",
            "status",
            "created_by_user_id",
            "published_by_user_id",
            "published_at",
        )
        read_only_fields = (
            "id",
            "status",
            "created_by_user_id",
            "published_by_user_id",
            "published_at",
        )


class LeaveCalendarDateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendarDate
        fields = ("id", "calendar", "day", "name", "is_restricted_holiday", "is_closed_day")

    def validate(self, attrs):
        calendar = attrs.get("calendar", getattr(self.instance, "calendar", None))
        day = attrs.get("day", getattr(self.instance, "day", None))
        if calendar is not None and day is not None and day.year != calendar.year:
            raise serializers.ValidationError(
                {"day": "The date must belong to the selected calendar year."}
            )
        return attrs


class LeaveHierarchySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveHierarchy
        fields = (
            "id",
            "unit_key",
            "unit_head_user_id",
            "establishment_user_id",
            "sanctioning_authority_user_id",
            "director_user_id",
            "active",
        )
        read_only_fields = ("id",)

    def validate(self, attrs):
        active = attrs.get("active", getattr(self.instance, "active", True))
        unit_head = attrs.get(
            "unit_head_user_id", getattr(self.instance, "unit_head_user_id", None)
        )
        sanctioner = attrs.get(
            "sanctioning_authority_user_id",
            getattr(self.instance, "sanctioning_authority_user_id", None),
        )
        if active and not unit_head:
            raise serializers.ValidationError(
                {"unit_head_user_id": "An active hierarchy requires a Unit Head."}
            )
        if active and not sanctioner:
            raise serializers.ValidationError(
                {
                    "sanctioning_authority_user_id": (
                        "An active hierarchy requires a sanctioning authority."
                    )
                }
            )
        for field in (
            "unit_head_user_id",
            "establishment_user_id",
            "sanctioning_authority_user_id",
            "director_user_id",
        ):
            user_id = attrs.get(field, getattr(self.instance, field, None))
            if user_id is not None and not 1 <= user_id <= 2147483647:
                raise serializers.ValidationError(
                    {field: "Must be a positive 32-bit user ID or blank."}
                )
        return attrs


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = (
            "id",
            "name",
            "start_date",
            "end_date",
            "external_reference",
            "active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start is not None and end is not None and end < start:
            raise serializers.ValidationError({"end_date": "End date must not precede start date."})
        return attrs
