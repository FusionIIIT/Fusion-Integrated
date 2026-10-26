from rest_framework import serializers
from modules.elm.models import LeaveType, LeaveBalance, LeaveApplication


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "max_days_per_year", "requires_document", "is_active"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "year", "allotted", "used", "available"]

    def get_available(self, obj):
        return obj.allotted - obj.used


class LeaveApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "start_date",
            "end_date",
            "half_day_period",
            "days",
            "reason",
            "status",
            "approver_id",
            "remarks",
            "decided_at",
            "created_at",
        ]
        read_only_fields = fields


class ApplyInputSerializer(serializers.Serializer):
    leave_type = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(max_length=2000)
    half_day_period = serializers.ChoiceField(
        choices=[
            ("FIRST_HALF", "First Half"),
            ("SECOND_HALF", "Second Half"),
        ],
        required=False,
        default="",
    )

class DecisionInputSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(max_length=2000, required=False, allow_blank=True)

