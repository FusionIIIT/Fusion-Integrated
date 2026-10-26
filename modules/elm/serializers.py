from rest_framework import serializers
from .models import (
    LeaveType,
    LeaveBalance,
    LeaveApplication,
    LeaveSubstitute,
    LeaveApproval,
    LeaveCalendarPeriod,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = "__all__"
        read_only_fields = ("id", "user_id", "created_at", "updated_at")


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)

    class Meta:
        model = LeaveApplication
        fields = "__all__"
        read_only_fields = (
            "id", "user_id", "status", "created_at", "updated_at"
        )

    def validate(self, attrs):
        start_date = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end_date = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before start date."}
            )
        return attrs


class LeaveSubstituteSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveSubstitute
        fields = "__all__"
        read_only_fields = ("id", "user_id", "status", "created_at", "updated_at")


class LeaveApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApproval
        fields = "__all__"
        read_only_fields = (
            "id", "user_id", "decision", "decided_at",
            "created_at", "updated_at"
        )
class LeaveCalendarPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveCalendarPeriod
        fields = "__all__"
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        start_date = attrs.get(
            "start_date",
            getattr(self.instance, "start_date", None),
        )
        end_date = attrs.get(
            "end_date",
            getattr(self.instance, "end_date", None),
        )
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({
                "end_date": "End date cannot precede start date."
            })
        return attrs
