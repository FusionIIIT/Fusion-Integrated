"""Serializers for Employee Leave Management endpoints."""

from rest_framework import serializers

from modules.leave.models import (
    LeaveBalance,
    LeaveRequest,
    LeaveType,
    ResumptionRecord,
    SubstituteNomination,
)


class LeaveHealthResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    module = serializers.CharField()


class LeaveActionResponseSerializer(serializers.Serializer):
    status = serializers.CharField()
    message = serializers.CharField(required=False, default="")


class LeaveTypeSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = [
            "code",
            "name",
            "is_continuous_count",
            "allows_half_day",
            "requires_substitute",
            "allows_extension",
            "carries_forward",
        ]


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSummarySerializer(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "year",
            "credited_days",
            "used_days",
            "available_days",
            "leave_type",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSummarySerializer(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "application_number",
            "user_id",
            "cadre",
            "department",
            "start_date",
            "end_date",
            "is_half_day",
            "half_day_period",
            "requested_days",
            "reason",
            "address_during_leave",
            "contact_number",
            "is_station_leave",
            "station_departure_date",
            "station_arrival_date",
            "station_destination",
            "status",
            "current_handler_role",
            "unit_head_recommendation",
            "unit_head_remarks",
            "cancellation_reason",
            "cancellation_requested_at",
            "extension_end_date",
            "extension_days",
            "extension_reason",
            "actual_days",
            "excess_days",
            "requires_admin_review",
            "reconciliation_status",
            "is_offline_record",
            "offline_sanction_reference",
            "offline_sanctioned_by",
            "offline_sanctioned_date",
            "created_at",
            "leave_type",
        ]


class SubstituteNominationSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)

    class Meta:
        model = SubstituteNomination
        fields = [
            "id",
            "substitute_user_id",
            "status",
            "remarks",
            "responded_at",
            "sequence",
            "request",
        ]


class ResumptionRecordSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(source="request.id", read_only=True)

    class Meta:
        model = ResumptionRecord
        fields = [
            "id",
            "request_id",
            "expected_date",
            "actual_resumption_date",
            "nature",
            "difference_days",
            "remarks",
            "reviewed_by_user_id",
            "reviewed_at",
            "decision",
        ]


# Request payload serializers


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type_code = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False, required=False)
    half_day_period = serializers.CharField(
        max_length=15, default="", required=False, allow_blank=True
    )
    is_station_leave = serializers.BooleanField(default=False, required=False)
    station_departure_date = serializers.DateField(required=False, allow_null=True)
    station_arrival_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(
        max_length=150, default="", required=False, allow_blank=True
    )
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    address_during_leave = serializers.CharField(default="", required=False, allow_blank=True)
    contact_number = serializers.CharField(
        max_length=30, default="", required=False, allow_blank=True
    )


class SubstituteResponseSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["accepted", "declined"])
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class LeaveWithdrawSerializer(serializers.Serializer):
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class LeaveCancelSerializer(serializers.Serializer):
    reason = serializers.CharField()


class LeaveExtendSerializer(serializers.Serializer):
    extension_end_date = serializers.DateField()
    reason = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveResumeSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class LeaveReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class LeaveSanctionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class ResumptionReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=["approved", "rejected"], default="approved", required=False
    )
    remarks = serializers.CharField(default="", required=False, allow_blank=True)


class OfflineLeaveCreateSerializer(serializers.Serializer):
    employee_user_id = serializers.IntegerField()
    leave_type_code = serializers.CharField(max_length=10)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField()
    offline_sanction_reference = serializers.CharField(max_length=100)
    offline_sanctioned_by = serializers.CharField(max_length=100)
    offline_sanctioned_date = serializers.DateField()
    is_half_day = serializers.BooleanField(default=False, required=False)
    half_day_period = serializers.CharField(
        max_length=15, default="", required=False, allow_blank=True
    )
