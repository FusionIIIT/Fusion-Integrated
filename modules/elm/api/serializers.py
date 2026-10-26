"""Serializers for Employee Leave Management endpoints."""
from rest_framework import serializers

from modules.elm.models import (
    HolidayCalendar,
    LeaveApplication,
    LeaveBalance,
    LeaveRolloverRecord,
    LeaveType,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            "id",
            "code",
            "name",
            "annual_quota",
            "can_carry_forward",
            "requires_substitute",
            "is_active",
        )
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    remaining = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )

    class Meta:
        model = LeaveBalance
        fields = (
            "id",
            "user_id",
            "leave_type",
            "year",
            "allocated",
            "used",
            "pending",
            "remaining",
        )
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    total_days = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )
    resumption_days_adjusted = serializers.DecimalField(
        max_digits=5, decimal_places=1, read_only=True
    )

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day",
            "station_leave",
            "station_address",
            "reason",
            "substitute_user_id",
            "substitute_status",
            "status",
            "reviewer_user_id",
            "review_remarks",
            "decided_at",
            "total_days",
            "original_application_id",
            "is_extension",
            "cancellation_status",
            "cancellation_reason",
            "cancellation_reviewer_user_id",
            "cancellation_remarks",
            "cancellation_decided_at",
            "actual_resumption_date",
            "resumption_status",
            "resumption_reviewer_user_id",
            "resumption_remarks",
            "resumption_decided_at",
            "resumption_days_adjusted",
            "is_balance_refunded",
            "is_offline",
            "sanction_reference",
            "sanction_date",
            "sanction_authority_name",
            "recommendation",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type_code = serializers.CharField(max_length=16)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.BooleanField(required=False, default=False)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=""
    )
    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )


class SubstituteDecisionSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=("accepted", "declined"), required=False
    )
    decision = serializers.ChoiceField(
        choices=("accepted", "declined"), required=False
    )

    def validate(self, attrs):
        status_val = attrs.get("status") or attrs.get("decision")
        if not status_val:
            raise serializers.ValidationError(
                "Either 'decision' or 'status' must be provided ('accepted' or 'declined')."
            )
        attrs["decision"] = status_val
        return attrs


class SubstituteReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class LeaveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=("recommended", "not_recommended", "approved", "rejected")
    )
    remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class LeaveCancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True, allow_blank=False)


class LeaveCancellationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=("recommended", "not_recommended", "approved", "rejected")
    )
    remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class LeaveExtensionCreateSerializer(serializers.Serializer):
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )


class DutyResumptionSubmitSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class DutyResumptionReviewSerializer(serializers.Serializer):
    remarks = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class OfflineLeaveCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    leave_type_code = serializers.CharField(max_length=16)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    sanction_reference = serializers.CharField(max_length=128)
    sanction_date = serializers.DateField()
    sanction_authority_name = serializers.CharField(max_length=128)
    reason = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class LeaveRolloverExecuteSerializer(serializers.Serializer):
    target_year = serializers.IntegerField()


class LeaveRolloverRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRolloverRecord
        fields = (
            "id",
            "user_id",
            "year",
            "cl_lapsed",
            "rh_lapsed",
            "scl_lapsed",
            "vl_converted",
            "el_credited_from_vl",
            "el_carried_forward",
            "col_carried_forward",
            "created_at",
        )
        read_only_fields = fields


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ("id", "date", "title", "is_restricted")
        read_only_fields = fields
