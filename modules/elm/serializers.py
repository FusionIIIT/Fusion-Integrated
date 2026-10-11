from rest_framework import serializers

from .models import Employee, LeaveRequest


class EmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ("id", "user_id", "name", "department")
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.CharField(source="employee.name", read_only=True)
    duration_days = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            "id", "employee", "employee_name", "start_date", "end_date",
            "duration_days", "status", "reason", "decision_note",
            "decided_by_id", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "employee", "employee_name", "duration_days", "status",
            "decision_note", "decided_by_id", "created_at", "updated_at",
        )

    def validate(self, attrs):
        start = attrs.get("start_date", getattr(self.instance, "start_date", None))
        end = attrs.get("end_date", getattr(self.instance, "end_date", None))
        if start and end and end < start:
            raise serializers.ValidationError({
                "end_date": "End date cannot be earlier than start date."
            })
        return attrs
