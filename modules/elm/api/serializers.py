from rest_framework import serializers
from rest_framework.serializers import ModelSerializer, SerializerMethodField

from modules.elm.models import LeaveApplication, LeaveBalance, LeaveType


class LeaveTypeSerializer(ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "max_days_per_year", "requires_document", "is_active"]


class LeaveBalanceSerializer(ModelSerializer):
    available = SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "year", "allotted", "used", "available"]

    def get_available(self, obj) -> int:
        return obj.allotted - obj.used


class LeaveApplicationSerializer(ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id", "employee_id", "leave_type", "start_date", "end_date", "days", "reason",
            "status", "approver_id", "remarks", "decided_at", "created_at",
        ]
        read_only_fields = fields


class ApplyInputSerializer(serializers.Serializer):
    leave_type = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)


class DecisionInputSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, max_length=2000)


class LeaveTypeCreateInputSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=16)
    name = serializers.CharField(max_length=128)
    max_days_per_year = serializers.IntegerField(min_value=0, max_value=366)
    requires_document = serializers.BooleanField(required=False, default=False)


class AllotInputSerializer(serializers.Serializer):
    employee_id = serializers.IntegerField()
    leave_type_id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    allotted = serializers.IntegerField(min_value=0, max_value=366)
