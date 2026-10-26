"""Serializers for Employee Leave Management REST API."""
from rest_framework import serializers

from modules.leave.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    LeaveWorkflowHistory,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "id",
            "code",
            "name",
            "max_days_per_year",
            "requires_substitute",
            "is_continuous_counting",
            "can_carry_forward",
            "is_active",
            "description",
        ]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "date", "is_restricted", "year", "description"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "year",
            "credited",
            "consumed",
            "carried_forward",
            "available",
        ]


class LeaveWorkflowHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveWorkflowHistory
        fields = [
            "id",
            "actor_id",
            "action",
            "from_state",
            "to_state",
            "remarks",
            "created_at",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    history = LeaveWorkflowHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "leave_days",
            "reason",
            "status",
            "is_half_day",
            "half_day_period",
            "station_leave_required",
            "departure_date",
            "arrival_date",
            "station_address",
            "emergency_contact",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "substitute_responded_at",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_action_at",
            "sanctioning_authority_id",
            "sanction_remarks",
            "sanctioned_at",
            "cancellation_reason",
            "cancellation_requested_at",
            "resumption_date",
            "resumption_remarks",
            "resumption_status",
            "resumption_reviewer_id",
            "resumption_reviewed_at",
            "history",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "applicant_id",
            "leave_days",
            "status",
            "substitute_status",
            "substitute_remarks",
            "substitute_responded_at",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_action_at",
            "sanctioning_authority_id",
            "sanction_remarks",
            "sanctioned_at",
            "cancellation_reason",
            "cancellation_requested_at",
            "resumption_status",
            "resumption_reviewer_id",
            "resumption_reviewed_at",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type = serializers.PrimaryKeyRelatedField(
        queryset=LeaveType.objects.filter(is_active=True)
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=[("FIRST_HALF", "First Half"), ("SECOND_HALF", "Second Half")],
        required=False,
        allow_blank=True,
        default="",
    )
    substitute_id = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave_required = serializers.BooleanField(default=False)
    departure_date = serializers.DateField(required=False, allow_null=True, default=None)
    arrival_date = serializers.DateField(required=False, allow_null=True, default=None)
    station_address = serializers.CharField(required=False, allow_blank=True, default="")
    emergency_contact = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveSubstituteResponseSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveReplacementSubstituteSerializer(serializers.Serializer):
    substitute_id = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveReviewActionSerializer(serializers.Serializer):
    review_action = serializers.ChoiceField(choices=["approve", "reject", "recommend"])
    recommendation = serializers.ChoiceField(
        choices=["RECOMMENDED", "NOT_RECOMMENDED"], required=False, allow_blank=True, default=""
    )
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveWithdrawSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveCancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LeaveCancellationReviewSerializer(serializers.Serializer):
    approval_action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveResumptionSubmitSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveResumptionReviewSerializer(serializers.Serializer):
    approval_action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
