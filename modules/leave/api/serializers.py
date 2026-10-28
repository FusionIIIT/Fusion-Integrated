from rest_framework import serializers

from modules.leave.models import (
    Holiday,
    LeaveAccount,
    LeaveApplication,
    LeaveTask,
    LeaveTransition,
    SubstituteNomination,
    VacationPeriod,
)


class LeaveAccountSerializer(serializers.ModelSerializer):
    remaining = serializers.DecimalField(max_digits=8, decimal_places=2,
                                         read_only=True)

    class Meta:
        model = LeaveAccount
        fields = ["id", "category", "year", "entitlement", "carried_forward",
                  "availed", "remaining"]


class LeaveTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = ["id", "from_status", "to_status", "actor_user_id",
                  "actor_role", "reason", "at"]


class SubstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteNomination
        fields = ["id", "substitute_user_id", "status", "responded_at"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    substitutes = SubstituteSerializer(many=True, read_only=True)
    transitions = LeaveTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = ["id", "applicant_user_id", "category", "starts_on", "ends_on",
                  "half_day", "purpose", "leave_days", "status",
                  "station_leave", "station_leave_place", "station_leave_reason",
                  "unit_head_user_id", "sanction_authority_user_id",
                  "resumption_on", "decided_at", "decision_note",
                  "substitutes", "transitions", "created_at"]


class ApplyLeaveSerializer(serializers.Serializer):
    category = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    half_day = serializers.ChoiceField(
        choices=["none", "first_half", "second_half"], default="none")
    purpose = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave = serializers.BooleanField(default=False)
    station_leave_place = serializers.CharField(required=False, allow_blank=True,
                                                default="")
    station_leave_reason = serializers.CharField(required=False, allow_blank=True,
                                                 default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)


class DecisionSerializer(serializers.Serializer):
    to_status = serializers.CharField()
    actor_role = serializers.ChoiceField(
        choices=["unit_head", "sanctioning_authority"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSerializer(serializers.Serializer):
    resumption_on = serializers.DateField()


class ExtensionSerializer(serializers.Serializer):
    ends_on = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineLeaveSerializer(serializers.Serializer):
    applicant_user_id = serializers.IntegerField()
    category = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reference = serializers.CharField()
    purpose = serializers.CharField(required=False, allow_blank=True, default="")


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "on_date", "name", "kind", "published"]


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "label", "starts_on", "ends_on"]


class LeaveTaskSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTask
        fields = ["id", "application", "assigned_user_id", "due_at",
                  "reminded_at", "escalated_at", "is_open"]
