from rest_framework import serializers

from modules.elm.models.leave_application import LeaveApplication
from modules.elm.models.leave_types import LeaveBalance, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = "__all__"


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "purpose",
            "station_leave_details",
            "substitute_id",
            "status",
            "decision_maker_id",
            "decision_date",
            "created_at",
            "updated_at",
            "unit_head_recommendation",
        ]
        read_only_fields = [
            "user_id",
            "status",
            "decision_maker_id",
            "decision_date",
            "unit_head_recommendation",
        ]
