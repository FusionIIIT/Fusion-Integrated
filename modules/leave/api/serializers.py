from rest_framework import serializers

from modules.leave.models import (
    LeaveBalance,
    LeaveManagerAssignment,
    LeaveRequest,
    LeaveType,
)


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "annual_allowance"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    available_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ["id", "leave_type", "leave_type_name", "year", "allocated_days",
                  "carried_days", "available_days"]
        read_only_fields = fields

    def get_available_days(self, obj):
        used = sum(LeaveRequest.objects.filter(
            user_id=obj.user_id, leave_type=obj.leave_type, start_date__year=obj.year,
            status__in=["pending", "approved"]).values_list("days", flat=True))
        return max(0, obj.allocated_days + obj.carried_days - used)


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    employee_name = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ["id", "user_id", "leave_type", "leave_type_name", "start_date",
                  "end_date", "days", "reason", "status", "review_note", "created_at",
                  "employee_name"]
        read_only_fields = ["id", "days", "status", "review_note", "created_at"]

    def get_employee_name(self, obj) -> str:
        names = self.context.get("employee_names", {})
        return names.get(obj.user_id, f"Employee #{obj.user_id}")


class ReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True)


class LeaveTypeConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "annual_allowance", "is_active"]
        read_only_fields = ["id"]

    def validate_annual_allowance(self, value):
        if value < 0:
            raise serializers.ValidationError("Allowance cannot be negative.")
        return value


class LeaveBalanceConfigurationSerializer(serializers.ModelSerializer):
    user_id = serializers.IntegerField(min_value=1)
    year = serializers.IntegerField(min_value=1, max_value=32767)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_type", "year", "allocated_days",
                  "carried_days"]
        read_only_fields = ["id"]

    def validate(self, attrs):
        for field in ("allocated_days", "carried_days"):
            value = attrs.get(field)
            if value is not None and value < 0:
                raise serializers.ValidationError({field: "Days cannot be negative."})
        return attrs


class LeaveManagerAssignmentSerializer(serializers.ModelSerializer):
    manager_user_id = serializers.IntegerField(min_value=1)
    employee_user_id = serializers.IntegerField(min_value=1)

    class Meta:
        model = LeaveManagerAssignment
        fields = ["id", "manager_user_id", "employee_user_id", "assigned_by_user_id"]
        read_only_fields = ["id", "assigned_by_user_id"]
        validators = []

    def validate(self, attrs):
        manager_id = attrs.get("manager_user_id")
        employee_id = attrs.get("employee_user_id")
        if manager_id == employee_id:
            raise serializers.ValidationError(
                {"employee_user_id": "A manager cannot be assigned to themselves."})
        return attrs
