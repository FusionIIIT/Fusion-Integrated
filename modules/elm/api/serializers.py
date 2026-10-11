from rest_framework import serializers
from modules.elm.models import LeaveBalance, LeaveApplication, LeaveActionHistory, Holiday


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_balance = serializers.FloatField(read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "year",
            "leave_type",
            "allocated",
            "availed",
            "pending",
            "available_balance",
        ]


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = [
            "id",
            "actor_user_id",
            "action",
            "comments",
            "created_at",
        ]


class LeaveApplicationReadSerializer(serializers.ModelSerializer):
    actions = LeaveActionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "start_half",
            "end_date",
            "end_half",
            "days_requested",
            "reason",
            "station_leave",
            "station_address",
            "station_contact",
            "emergency_contact",
            "substitute_user_id",
            "unit_head_user_id",
            "sanctioning_authority_user_id",
            "status",
            "remarks",
            "created_at",
            "updated_at",
            "actions",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type = serializers.CharField(max_length=8)
    start_date = serializers.DateField()
    start_half = serializers.CharField(default="FULL")
    end_date = serializers.DateField()
    end_half = serializers.CharField(default="FULL")
    reason = serializers.CharField(max_length=1000)
    station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(max_length=255, required=False, allow_blank=True)
    station_contact = serializers.CharField(max_length=32, required=False, allow_blank=True)
    emergency_contact = serializers.CharField(max_length=32, required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ReviewActionSerializer(serializers.Serializer):
    recommend = serializers.BooleanField()
    comments = serializers.CharField(max_length=500, required=False, allow_blank=True)


class SanctionActionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    comments = serializers.CharField(max_length=500, required=False, allow_blank=True)


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "date", "name", "is_restricted"]
