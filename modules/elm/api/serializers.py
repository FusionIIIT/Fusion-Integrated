from rest_framework import serializers

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "leave_type"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ["id", "employee_id", "leave_type", "balance"]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "applicant_id",
            "leave_type",
            "start_date",
            "end_date",
            "station_leave_details",
            "status",
        ]
