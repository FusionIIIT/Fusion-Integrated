from rest_framework import serializers

from .models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining_days = serializers.ReadOnlyField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["id", "user_id", "leave_type", "leave_type_name", "year", "total_days", "used_days", "remaining_days"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    employee_name = serializers.SerializerMethodField()
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_user_id",
            "employee_name",
            "leave_type",
            "leave_type_name",
            "start_date",
            "end_date",
            "reason",
            "status",
            "remarks",
            "reviewed_by_user_id",
            "reviewed_at",
            "created_at",
        ]
        read_only_fields = ["employee_user_id", "status", "remarks", "reviewed_by_user_id", "reviewed_at", "created_at"]

    def get_employee_name(self, obj):
        return f"User {obj.employee_user_id}"

    def validate(self, attrs):
        start_date = attrs.get("start_date") or (self.instance.start_date if self.instance else None)
        end_date = attrs.get("end_date") or (self.instance.end_date if self.instance else None)
        if start_date and end_date and end_date < start_date:
            raise serializers.ValidationError({"end_date": "End date cannot be before start date."})
        return attrs

    def create(self, validated_data):
        request = self.context.get("request")
        if request and hasattr(request, "principal") and request.principal:
            validated_data["employee_user_id"] = request.principal.user_id
        return super().create(validated_data)


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
