from rest_framework import serializers
from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationAudit,
    LeaveBalance,
    HolidayCalendar,
    LeaveCategory,
    HalfDaySlot,
    LeaveStatus,
    SubstituteStatus,
    UnitHeadRecommendation,
)


class LeaveApplicationAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplicationAudit
        fields = [
            "id",
            "actor_id",
            "action",
            "from_status",
            "to_status",
            "remarks",
            "created_at",
        ]
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    audits = LeaveApplicationAuditSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day_slot",
            "calculated_days",
            "reason",
            "status",
            "station_leave_applied",
            "station_leave_address",
            "station_leave_contact",
            "station_leave_start",
            "station_leave_end",
            "substitute_id",
            "substitute_status",
            "substitute_remarks",
            "unit_head_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_authority_id",
            "sanctioner_remarks",
            "decided_at",
            "cancelled_at",
            "cancellation_reason",
            "actual_resumption_date",
            "created_at",
            "updated_at",
            "audits",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "calculated_days",
            "status",
            "substitute_status",
            "unit_head_recommendation",
            "decided_at",
            "cancelled_at",
            "actual_resumption_date",
            "created_at",
            "updated_at",
            "audits",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day_slot = serializers.ChoiceField(choices=HalfDaySlot.choices, default=HalfDaySlot.NONE)
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    unit_head_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    sanctioning_authority_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    station_leave_applied = serializers.BooleanField(default=False)
    station_leave_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_leave_contact = serializers.CharField(required=False, allow_blank=True, default="")
    submit_now = serializers.BooleanField(default=True)

    def validate(self, attrs):
        start_date = attrs.get("start_date")
        end_date = attrs.get("end_date")
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError({
                "start_date": "Start date must be on or before end date."
            })

        category = attrs.get("category")
        half_day_slot = attrs.get("half_day_slot", HalfDaySlot.NONE)
        if half_day_slot != HalfDaySlot.NONE:
            if category != LeaveCategory.CL:
                raise serializers.ValidationError({
                    "half_day_slot": "Half-day leave is valid strictly for Casual Leave (CL)."
                })
            if start_date != end_date:
                raise serializers.ValidationError({
                    "half_day_slot": "Half-day leave can only be taken on a single calendar date."
                })

        if attrs.get("station_leave_applied", False):
            address = attrs.get("station_leave_address", "")
            contact = attrs.get("station_leave_contact", "")
            if not address or not address.strip():
                raise serializers.ValidationError({
                    "station_leave_address": "Address during station leave is required."
                })
            if not contact or not contact.strip():
                raise serializers.ValidationError({
                    "station_leave_contact": "Emergency contact number during station leave is required."
                })

        return attrs


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadReviewSerializer(serializers.Serializer):
    approve_or_recommend = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class CancellationRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField(required=True)
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "category",
            "credited",
            "availed",
            "available_balance",
        ]
        read_only_fields = fields


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = [
            "id",
            "name",
            "date",
            "is_rh",
            "year",
        ]
        read_only_fields = fields
