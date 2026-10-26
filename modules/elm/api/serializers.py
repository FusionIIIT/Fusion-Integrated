from rest_framework import serializers

from ..models import Employee, HolidayCalendar, LeaveApplication, LeavePolicy


class LeavePolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    allowed_actions = serializers.SerializerMethodField()

    def get_allowed_actions(self, application):
        employee = self.context.get("employee")
        if employee is None:
            return []
        from ..services import current_hierarchy, establishment_allowed

        state = application.state
        if state == "Awaiting Substitute Response" and application.substitute_id == employee.pk:
            return ["substitute-response"]
        if state == "Awaiting Unit Head Review" and application.unit_head_id == employee.pk:
            return ["unit-head-review"]
        if (
            state == "Awaiting Final Sanction Decision"
            and application.sanctioning_authority_id == employee.pk
        ):
            return ["final-decision"]
        if (
            state == "Awaiting Director Self-Sanction"
            and application.applicant_id == employee.pk
            and employee.is_director
        ):
            return ["director-decision"]
        request = self.context.get("request")
        principal = getattr(request, "principal", None)
        if state == "Awaiting Establishment Routing" and establishment_allowed(
            principal, current_hierarchy()
        ):
            return ["establishment-route"]
        return []

    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = [field.name for field in LeaveApplication._meta.fields]


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["id", "name"]


class ApplicationInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveApplication._meta.get_field("category").choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    first_half = serializers.BooleanField(default=False)
    second_half = serializers.BooleanField(default=False)
    substitute = serializers.PrimaryKeyRelatedField(
        queryset=Employee.objects.filter(user__is_active=True, user__kind__in=["staff", "faculty"]),
        required=False,
        allow_null=True,
    )
    station_leave_details = serializers.JSONField(required=False)
    remarks = serializers.CharField(required=False, allow_blank=True)


class SubstituteInputSerializer(serializers.Serializer):
    accept = serializers.BooleanField(required=True)


class DecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=["Approve", "Reject", "Recommended", "Not Recommended"]
    )
