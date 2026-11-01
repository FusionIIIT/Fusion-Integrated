"""DRF Serializers for ELM module."""
from rest_framework import serializers

from modules.elm.models.balances import LeaveBalance
from modules.elm.models.holidays import HolidayCalendar
from modules.elm.models.leaves import LeaveRequest, LeaveTransitionHistory


class LeaveTransitionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransitionHistory
        fields = ["id", "from_status", "to_status", "actor_user_id", "remarks", "created_at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    transitions = LeaveTransitionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "user_id", "category", "start_date", "end_date",
            "is_half_day", "half_day_period", "days_calculated", "reason",
            "status", "leaving_station", "station_start_date", "station_end_date",
            "station_address", "emergency_phone", "substitute_user_id",
            "substitute_status", "unit_head_user_id", "unit_head_recommendation",
            "unit_head_remarks", "sanctioning_authority_user_id", "sanctioned_at",
            "is_offline_sanctioned", "offline_sanction_reference",
            "is_extension", "original_leave_id",
            "created_at", "updated_at", "transitions",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveRequest.CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.ChoiceField(
        choices=LeaveRequest.HALF_DAY_CHOICES, required=False, allow_null=True
    )
    reason = serializers.CharField(max_length=1000)
    leaving_station = serializers.BooleanField(default=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    emergency_phone = serializers.CharField(max_length=32, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    unit_head_user_id = serializers.IntegerField(required=False, allow_null=True)


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id", "user_id", "year", "category",
            "credited_balance", "carried_forward", "availed_balance", "available_balance",
        ]


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "end_date", "name", "holiday_type", "year", "is_published"]


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()


class UnitHeadReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    remarks = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SanctionDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(max_length=500, required=False, allow_blank=True)


class LeaveExtensionCreateSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=1000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
