"""Leave module DRF serializers."""
from rest_framework import serializers

from modules.leave.models import LeaveBalance, LeaveRequest


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "category", "credited", "availed", "balance", "lapsed", "year"]


class LeaveRequestReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "start_date",
            "end_date",
            "half_day",
            "requested_days",
            "purpose",
            "status",
            "station_leave",
            "station_start_date",
            "station_end_date",
            "station_address",
            "station_contact",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "unit_head_user_id",
            "unit_head_decision",
            "unit_head_remarks",
            "sanctioning_authority_user_id",
            "sanctioning_decision",
            "sanctioning_remarks",
            "parent_leave_id",
            "actual_resumption_date",
            "resumption_verified",
            "restored_days",
            "is_offline",
            "offline_reference",
            "created_at",
            "updated_at",
        ]


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    half_day = serializers.CharField(default="full", required=False)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave = serializers.BooleanField(default=False, required=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_address = serializers.CharField(default="", required=False, allow_blank=True)
    station_contact = serializers.CharField(default="", required=False, allow_blank=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, default="", allow_blank=True)


class LeaveReviewSerializer(serializers.Serializer):
    decision = serializers.CharField()
    remarks = serializers.CharField(required=False, default="", allow_blank=True)


class ResumptionSerializer(serializers.Serializer):
    actual_date = serializers.DateField()


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    offline_reference = serializers.CharField()
    year = serializers.IntegerField(default=2026, required=False)
