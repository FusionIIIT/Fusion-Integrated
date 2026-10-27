"""REST API serializers for Employee Leave Management."""
from rest_framework import serializers

from modules.elm.models import (
    HolidayCalendarEntry,
    LeaveAccount,
    LeaveCategory,
    LeavePolicyConfig,
    LeaveRequest,
    LeaveResumptionRecord,
    LeaveStatus,
    LeaveTransaction,
    SubstituteAssignment,
)


class SubstituteAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubstituteAssignment
        fields = ["id", "substitute_id", "status", "remarks", "responded_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    substitute_assignments = SubstituteAssignmentSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "applicant_id",
            "category",
            "start_date",
            "end_date",
            "duration_days",
            "is_half_day",
            "half_day_type",
            "reason",
            "is_station_leave",
            "station_address",
            "emergency_contact",
            "status",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_authority_remarks",
            "substitute_assignments",
            "created_at",
            "updated_at",
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    substitute_id = serializers.IntegerField(required=False, allow_null=True)
    is_half_day = serializers.BooleanField(default=False)
    half_day_type = serializers.ChoiceField(
        choices=["first_half", "second_half"], required=False, allow_null=True
    )
    is_station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    emergency_contact = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewActionSerializer(serializers.Serializer):
    action = serializers.CharField()  # APPROVE, REJECT, RECOMMEND, NOT_RECOMMEND
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccount
        fields = ["id", "category", "year", "allotted", "used", "pending", "available"]


class LeaveTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransaction
        fields = ["id", "delta", "transaction_type", "reference_id", "created_at"]


class OfflineLeaveSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanction_reference = serializers.CharField()
    reason = serializers.CharField()
    is_station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
