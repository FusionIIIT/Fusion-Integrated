from drf_spectacular.utils import extend_schema_serializer
from rest_framework import serializers

from modules.leave.models import (
    HolidayCalendar,
    LeaveAccount,
    LeaveApplication,
    LeavePolicy,
    LeaveResumption,
)


class LeaveWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=("CL", "RH", "SCL", "EL", "COL", "VL"))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(
        choices=("", "first", "second"), required=False, allow_blank=True
    )
    purpose = serializers.CharField()
    station_leave = serializers.JSONField(required=False)
    medical_evidence = serializers.JSONField(required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


@extend_schema_serializer(component_name="LeaveApplication")
class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "category",
            "request_type",
            "base_leave_id",
            "start_date",
            "end_date",
            "half",
            "purpose",
            "station_leave",
            "medical_evidence",
            "chargeable_days",
            "substitute_required",
            "substitute_user_id",
            "state",
            "unit_head_user_id",
            "final_authority_user_id",
            "route",
            "recommendation",
            "decision_reason",
            "approved_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "user_id",
            "state",
            "chargeable_days",
            "approved_at",
            "created_at",
            "updated_at",
        )


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ("category", "year", "balance", "carried")


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = "__all__"


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = "__all__"


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveResumption
        fields = "__all__"
        read_only_fields = ("state", "reviewed_by", "reviewed_at")


class DecisionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=("approve", "reject"))
    recommendation = serializers.ChoiceField(
        choices=("recommended", "not_recommended"), required=False
    )
    reason = serializers.CharField(required=False, allow_blank=True)


class ExtensionSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class OfflineLeaveSerializer(LeaveWriteSerializer):
    employee_user_id = serializers.IntegerField()
    employee_kind = serializers.ChoiceField(choices=("faculty", "staff"))
    evidence = serializers.JSONField()


class HistorySerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    transitions = serializers.ListField(child=serializers.DictField())


class NotificationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    application_id = serializers.IntegerField()
    kind = serializers.CharField()
    read = serializers.BooleanField()
    created_at = serializers.DateTimeField()
