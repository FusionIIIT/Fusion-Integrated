"""Serializers for Employee Leave Management (ELM) endpoints."""
from rest_framework import serializers

from modules.elm.models.balances import LeaveAccountTransaction, LeaveBalance
from modules.elm.models.holidays import HolidayCalendar
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = [
            "id",
            "date",
            "name",
            "holiday_type",
            "year",
            "is_published",
        ]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(
        max_digits=5, decimal_places=2, read_only=True
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "category",
            "credited_balance",
            "carried_forward",
            "availed_balance",
            "available_balance",
            "updated_at",
        ]


class LeaveAccountTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAccountTransaction
        fields = [
            "id",
            "user_id",
            "year",
            "category",
            "transaction_type",
            "days",
            "remarks",
            "created_at",
        ]


class LeaveTransitionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransitionHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "remarks",
            "created_at",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    transitions = LeaveTransitionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "is_half_day",
            "half_day_period",
            "days_calculated",
            "reason",
            "status",
            "leaving_station",
            "station_start_date",
            "station_end_date",
            "station_address",
            "emergency_phone",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "unit_head_user_id",
            "unit_head_recommendation",
            "unit_head_remarks",
            "sanctioning_authority_user_id",
            "sanction_remarks",
            "sanctioned_at",
            "actual_resumption_date",
            "resumption_remarks",
            "created_at",
            "updated_at",
            "transitions",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=["CL", "RH", "SCL", "EL", "VL", "COL"]
    )
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=["first_half", "second_half"],
        required=False,
        allow_null=True,
    )
    leaving_station = serializers.BooleanField(default=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_address = serializers.CharField(
        max_length=255, required=False, allow_blank=True
    )
    emergency_phone = serializers.CharField(
        max_length=32, required=False, allow_blank=True
    )
    substitute_user_id = serializers.IntegerField(
        required=False, allow_null=True
    )
    unit_head_user_id = serializers.IntegerField(
        required=False, allow_null=True
    )
    sanctioning_authority_user_id = serializers.IntegerField(
        required=False, allow_null=True
    )

    def validate(self, attrs):
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and start > end:
            raise serializers.ValidationError(
                {"end_date": "end_date must not be before start_date."}
            )
        if attrs.get("is_half_day") and start and end and start != end:
            raise serializers.ValidationError(
                {"end_date": "Half-day leave must have identical start and end dates."}
            )
        if attrs.get("leaving_station"):
            if not attrs.get("station_address"):
                raise serializers.ValidationError(
                    {"station_address": "station_address is required when leaving_station is true."}
                )
            if not attrs.get("emergency_phone"):
                raise serializers.ValidationError(
                    {"emergency_phone": "emergency_phone is required when leaving_station is true."}
                )
        return attrs


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    remarks = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )


class UnitHeadReviewSerializer(serializers.Serializer):
    recommended = serializers.BooleanField()
    remarks = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )


class SanctionDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    remarks = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )


class CancellationSerializer(serializers.Serializer):
    remarks = serializers.CharField(
        max_length=500, required=False, allow_blank=True
    )


class ResumptionSerializer(serializers.Serializer):
    actual_resumption_date = serializers.DateField()
    remarks = serializers.CharField(
        max_length=1000, required=False, allow_blank=True
    )


class AdminBalanceCreditSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField()
    category = serializers.ChoiceField(
        choices=["CL", "RH", "SCL", "EL", "VL", "COL"]
    )
    credited_balance = serializers.DecimalField(max_digits=5, decimal_places=2)
