from rest_framework import serializers
from modules.elm.models import HolidayCalendar, LeaveActionHistory, LeaveBalance, LeaveRequest


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "employee_id", "leave_type", "year", "allocated", "availed", "balance"]


class LeaveActionHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveActionHistory
        fields = ["id", "actor_id", "action", "comments", "timestamp"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    actions = LeaveActionHistorySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "start_date",
            "end_date",
            "is_half_day",
            "half_day_period",
            "purpose",
            "is_station_leave",
            "station_details",
            "substitute_id",
            "substitute_status",
            "status",
            "remarks",
            "created_at",
            "updated_at",
            "actions",
        ]
        read_only_fields = ["id", "applicant_id", "substitute_status", "status", "created_at", "updated_at"]


class ApplyLeaveInputSerializer(serializers.Serializer):
    leave_type = serializers.CharField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    purpose = serializers.CharField()
    is_half_day = serializers.BooleanField(default=False)
    half_day_period = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    is_station_leave = serializers.BooleanField(default=False)
    station_details = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class DecisionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["RECOMMEND", "NOT_RECOMMEND", "APPROVE", "REJECT"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "name", "is_restricted", "year"]
