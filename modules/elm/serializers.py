
from rest_framework import serializers

from .models import LeaveType, LeaveBalance, LeaveRequest


class LeaveTypeSerializer(serializers.ModelSerializer):
    """Read-only representation of supported leave categories."""

    class Meta:
        model = LeaveType
        fields = ["id", "name", "type_code"]
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    """Representation of an employee's leave balance."""

    leave_type_display = serializers.CharField(
        source="leave_type.name",
        read_only=True,
    )
    leave_type_code = serializers.CharField(
        source="leave_type.type_code",
        read_only=True,
    )

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "leave_type",
            "leave_type_display",
            "leave_type_code",
            "current_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    """Representation of a leave request.

    IAM identity and approval fields are managed by the service layer.
    """

    leave_type_display = serializers.CharField(
        source="leave_type.name",
        read_only=True,
    )
    leave_type_code = serializers.CharField(
        source="leave_type.type_code",
        read_only=True,
    )
    user_id = serializers.IntegerField(read_only=True)
    approver_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "leave_type_display",
            "leave_type_code",
            "start_date",
            "end_date",
            "reason",
            "status",
            "approver_id",
            "approval_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "status",
            "approver_id",
            "approval_date",
            "created_at",
            "updated_at",
        ]

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
            raise serializers.ValidationError(
                {"end_date": "End date cannot be before start date."}
            )

        return attrs
