from rest_framework import serializers

from modules.directory import contracts as directory
from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = "__all__"


class LeaveBalanceSerializer(serializers.ModelSerializer):
    remaining_days = serializers.IntegerField(read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_name",
            "year",
            "total_days",
            "used_days",
            "remaining_days",
        ]


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
            "reviewed_by_user_id",
            "reviewed_at",
            "remarks",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "employee_user_id",
            "status",
            "reviewed_by_user_id",
            "reviewed_at",
            "remarks",
            "created_at",
            "updated_at",
        ]

    def get_employee_name(self, obj) -> str:
        people = self.context.get("people")
        if people is not None and obj.employee_user_id in people:
            return people[obj.employee_user_id].display_name
        try:
            person = directory.get_users([obj.employee_user_id]).get(obj.employee_user_id)
            if person:
                return person.display_name
        except (KeyError, ValueError, TypeError):
            pass
        return f"User {obj.employee_user_id}"

    def validate(self, attrs):
        if not attrs.get("leave_type") and not self.instance:
            raise serializers.ValidationError({"leave_type": "This field is required."})
        start_date = attrs.get("start_date") or (
            self.instance.start_date if self.instance else None
        )
        end_date = attrs.get("end_date") or (
            self.instance.end_date if self.instance else None
        )
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs


class LeaveApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")
