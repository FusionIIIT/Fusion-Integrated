from rest_framework import serializers
from modules.elm.models import (
    ApplicationTransition,
    EmployeeLeaveBalance,
    HolidayCalendar,
    LeaveApplication,
)


class EmployeeLeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = EmployeeLeaveBalance
        fields = [
            "id",
            "year",
            "leave_category",
            "allocated_days",
            "availed_days",
            "carried_forward",
            "pending_days",
            "available_days",
        ]


class ApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTransition
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "remarks",
            "created_at",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    transitions = ApplicationTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_category",
            "start_date",
            "end_date",
            "half_day_type",
            "calculated_days",
            "reason",
            "status",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "is_station_leave",
            "station_start_date",
            "station_end_date",
            "station_destination",
            "station_contact_address",
            "station_emergency_phone",
            "unit_head_recommendation",
            "unit_head_remarks",
            "final_decision",
            "final_decision_date",
            "final_remarks",
            "cancellation_reason",
            "is_extension",
            "resumption_date",
            "resumption_status",
            "resumption_remarks",
            "is_offline_sanctioned",
            "offline_sanction_reference",
            "transitions",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_category = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day_type = serializers.CharField(max_length=16, required=False, allow_blank=True, default="")
    reason = serializers.CharField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="")
    station_contact_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_emergency_phone = serializers.CharField(required=False, allow_blank=True, default="")


class ActionRemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadRecommendationSerializer(serializers.Serializer):
    recommendation = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "name", "is_restricted_holiday", "is_published", "year"]
