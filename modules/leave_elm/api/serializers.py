from rest_framework import serializers

from modules.leave_elm.models import LeaveApplication, LeaveBalance


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "year", "leave_type", "balance")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "purpose",
            "status",
            "is_station_leave",
            "station_address",
            "substitute_user_id",
            "substitute_accepted",
            "created_at",
        )
        read_only_fields = ("id", "user_id", "status", "substitute_accepted", "created_at")


class LeaveApplicationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = (
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "purpose",
            "is_station_leave",
            "station_address",
            "substitute_user_id",
        )
