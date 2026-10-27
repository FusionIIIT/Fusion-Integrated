"""Serializers for ELM module endpoints."""
from rest_framework import serializers

from modules.elm.models import (
    LeavePolicyConfig,
    HolidayCalendar,
    AcademicVacationPeriod,
    LeaveBalance,
    LeaveRequest,
    LeaveActionHistory,
    LeaveExtension,
    LeaveResumption,
    OfflineSanctionRecord,
)


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
            "consumed",
            "pending",
            "carried_forward",
            "available_balance",
        ]


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = [
            "id",
            "actor_id",
            "action",
            "previous_status",
            "new_status",
            "remarks",
            "created_at",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveActionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "duration_days",
            "purpose",
            "is_station_leave",
            "station_address",
            "station_contact",
            "station_start_date",
            "station_end_date",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "substitute_acted_at",
            "current_status",
            "current_assignee_role",
            "unit_head_recommendation",
            "unit_head_remarks",
            "unit_head_acted_at",
            "sanctioning_authority_role",
            "sanction_remarks",
            "sanction_acted_at",
            "final_decision_by_id",
            "is_offline_sanctioned",
            "offline_reference",
            "created_at",
            "updated_at",
            "actions",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "duration_days",
            "substitute_status",
            "current_status",
            "current_assignee_role",
            "unit_head_recommendation",
            "created_at",
            "updated_at",
            "actions",
        ]


class LeaveRequestCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    half_day = serializers.ChoiceField(
        choices=["none", "first_half", "second_half"], default="none"
    )
    is_station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(max_length=500, required=False, allow_blank=True)
    station_contact = serializers.CharField(max_length=64, required=False, allow_blank=True)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class SubstituteActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ApprovalActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineLeaveCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=["CL", "RH", "SCL", "EL", "COL", "VL"])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    offline_reference_no = serializers.CharField(max_length=128)
    sanctioning_authority_name = serializers.CharField(max_length=128)
    sanction_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "name", "date", "year", "holiday_type", "is_published"]


class AcademicVacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = AcademicVacationPeriod
        fields = ["id", "name", "start_date", "end_date", "academic_year", "is_active"]


class PolicyConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicyConfig
        fields = "__all__"
