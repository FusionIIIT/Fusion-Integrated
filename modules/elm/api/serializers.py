"""DRF Serializers for Leave Management (ELM).

Write serializers use explicit field definitions to prevent field mass-assignment vulnerabilities.
"""
from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveCategory, LeaveHistory


class LeaveCategorySerializer(serializers.ModelSerializer):
    """Serializer for leave categories."""

    class Meta:
        model = LeaveCategory
        fields = (
            "id",
            "code",
            "name",
            "description",
            "annual_quota",
            "carries_forward",
            "continuous_counting",
            "faculty_only",
        )
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Serializer for an employee's leave balance."""

    category = LeaveCategorySerializer(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "user_id",
            "category",
            "year",
            "credited",
            "consumed",
            "balance",
        )
        read_only_fields = fields


class LeaveHistorySerializer(serializers.ModelSerializer):
    """Audit log history entry for a leave application."""

    class Meta:
        model = LeaveHistory
        fields = (
            "id",
            "actor_id",
            "action",
            "from_status",
            "to_status",
            "remarks",
            "created_at",
        )
        read_only_fields = fields


class LeaveApplicationListSerializer(serializers.ModelSerializer):
    """Brief summary of a leave application for list views."""

    category_code = serializers.CharField(source="category.code", read_only=True)
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "category_code",
            "category_name",
            "start_date",
            "end_date",
            "half_day",
            "days_count",
            "status",
            "station_leave",
            "created_at",
        )
        read_only_fields = fields


class LeaveApplicationDetailSerializer(serializers.ModelSerializer):
    """Detailed view of a leave application including station and audit details."""

    category = LeaveCategorySerializer(read_only=True)
    history = LeaveHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "days_count",
            "reason",
            "status",
            "station_leave",
            "station_address",
            "station_start_date",
            "station_end_date",
            "emergency_contact",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "substitute_acted_at",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_acted_at",
            "sanctioning_authority_id",
            "sanction_remarks",
            "sanction_acted_at",
            "created_at",
            "updated_at",
            "history",
        )
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.Serializer):
    """Input payload to submit a new leave application."""

    category_code = serializers.CharField(max_length=20)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    half_day = serializers.ChoiceField(
        choices=LeaveApplication.HALF_DAY_CHOICES, default="none"
    )
    station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    station_start_date = serializers.DateField(
        required=False, allow_null=True, default=None
    )
    station_end_date = serializers.DateField(
        required=False, allow_null=True, default=None
    )
    emergency_contact = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    substitute_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )


class SubstituteResponseSerializer(serializers.Serializer):
    """Input payload when a nominated substitute accepts or declines."""

    action = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class WorkflowTransitionSerializer(serializers.Serializer):
    """Input payload for Unit Head or Sanctioning Authority decision."""

    action = serializers.ChoiceField(
        choices=["approve", "reject", "recommend", "not_recommend"]
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveWithdrawSerializer(serializers.Serializer):
    """Input payload when an applicant withdraws a pending leave request."""

    remarks = serializers.CharField(required=False, allow_blank=True, default="")
