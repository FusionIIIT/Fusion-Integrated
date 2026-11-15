from rest_framework import serializers

from modules.leave_elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveCategory,
    OfflineSanctionedLeaveRecord,
    PolicyConfiguration,
    SLAConfiguration,
)


class LeaveCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCategory
        fields = ("id", "code", "name")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    category = LeaveCategorySerializer(read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "category",
            "status",
            "starts_on",
            "ends_on",
            "half_day",
            "requested_days",
            "purpose",
            "station_leave",
            "station_destination",
            "substitute_user_id",
            "substitute_response",
            "submitted_at",
            "created_at",
        )
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category_id = serializers.IntegerField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    half_day = serializers.ChoiceField(choices=("full", "first", "second"), default="full")
    purpose = serializers.CharField(max_length=4000)
    station_leave = serializers.BooleanField(default=False)
    station_destination = serializers.CharField(
        max_length=160, required=False, allow_blank=True, default=""
    )
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    medical_evidence_reference = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )

    def validate(self, attrs):
        if attrs["ends_on"] < attrs["starts_on"]:
            raise serializers.ValidationError("ends_on must not precede starts_on")
        return attrs


class SubstituteResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=("accepted", "declined"))


class ReviewSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=("recommended", "not_recommended", "approved", "rejected")
    )
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    category = LeaveCategorySerializer(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "category",
            "year",
            "opening_balance",
            "credited",
            "used",
            "closing_balance",
        )
        read_only_fields = fields


class CancellationCreateSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000)


class ExtensionCreateSerializer(serializers.Serializer):
    additional_starts_on = serializers.DateField()
    additional_ends_on = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)

    def validate(self, attrs):
        if attrs["additional_ends_on"] < attrs["additional_starts_on"]:
            raise serializers.ValidationError(
                "additional_ends_on must not precede additional_starts_on"
            )
        return attrs


class ResumptionCreateSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    details = serializers.CharField(required=False, allow_blank=True, default="")


class PolicyConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyConfiguration
        fields = ("id", "category", "key", "value", "updated_at")
        read_only_fields = ("id", "updated_at")


class SLAConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SLAConfiguration
        fields = (
            "id",
            "workflow_name",
            "reminder_hours",
            "escalation_hours",
            "escalation_role",
            "is_active",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = (
            "id",
            "name",
            "year",
            "holidays",
            "restricted_holidays",
            "is_published",
            "published_at",
            "created_at",
        )
        read_only_fields = ("id", "is_published", "published_at", "created_at")


class OfflineLeaveCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfflineSanctionedLeaveRecord
        fields = (
            "user_id",
            "category",
            "starts_on",
            "ends_on",
            "leave_days",
            "purpose",
            "sanction_reference",
            "evidence_reference",
        )


class ReplacementSubstituteSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()
