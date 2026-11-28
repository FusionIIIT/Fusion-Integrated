from rest_framework import serializers

from modules.elm.models import (
    ApprovalRoute,
    EmployeeProfile,
    Holiday,
    HolidayCalendar,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestEvent,
    OrganizationUnit,
    VacationPeriod,
)


class LeaveRequestReadSerializer(serializers.ModelSerializer):
    events = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = "__all__"

    def get_events(self, obj):
        if not (
            self.context.get("include_events")
            or obj.employee_user_id == self.context["actor"].user_id
        ):
            return []
        return [
            {
                "action": e.action,
                "from_status": e.from_status,
                "to_status": e.to_status,
                "note": e.note,
                "at": e.at,
            }
            for e in obj.events.all()
        ]


class SubmitLeaveSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    cl_part = serializers.ChoiceField(choices=["", "first", "second"], required=False, default="")
    reason = serializers.CharField(max_length=1000)
    medical_evidence_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )
    station_leave = serializers.BooleanField(required=False, default=False)
    station_details = serializers.CharField(max_length=500, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=[
            "approve",
            "reject",
            "recommended",
            "not_recommended",
            "verify",
            "accept_substitute",
            "decline_substitute",
            "replace_substitute",
            "withdraw",
        ]
    )
    note = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class OrganizationUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationUnit
        fields = "__all__"


class EmployeeProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeProfile
        fields = "__all__"


class ApprovalRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalRoute
        fields = "__all__"

    def validate(self, attrs):
        authority = attrs.get(
            "authority_user_id", getattr(self.instance, "authority_user_id", None)
        )
        establishment = attrs.get(
            "is_establishment", getattr(self.instance, "is_establishment", False)
        )
        if not establishment and not authority:
            raise serializers.ValidationError(
                {"authority_user_id": "A named authority is required for a sanctioning route."}
            )
        return attrs


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"
        read_only_fields = ("published_at", "created_at", "updated_at")


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = "__all__"

    def validate_calendar(self, calendar):
        if calendar.status != "draft":
            raise serializers.ValidationError(
                "Published calendars are immutable; create a replacement draft."
            )
        return calendar


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = "__all__"


class LeaveRequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestEvent
        fields = "__all__"
