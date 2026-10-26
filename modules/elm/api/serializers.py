from rest_framework import serializers

from modules.elm.models import LeaveBalance, LeaveRequest, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ["id", "code", "name", "annual_quota", "requires_attachment", "is_active"]


class LeaveBalanceSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)
    remaining_days = serializers.DecimalField(max_digits=5, decimal_places=1, read_only=True)

    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "year",
            "total_allocated",
            "used_days",
            "remaining_days",
        ]


class LeaveRequestSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="leave_type.code", read_only=True)
    leave_type_name = serializers.CharField(source="leave_type.name", read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "employee_id",
            "leave_type",
            "leave_type_code",
            "leave_type_name",
            "start_date",
            "end_date",
            "total_days",
            "is_half_day",
            "reason",
            "contact_address",
            "substitute_employee_id",
            "status",
            "reviewer_id",
            "review_comment",
            "reviewed_at",
            "created_at",
        ]


class SubmitLeaveInputSerializer(serializers.Serializer):
    leave_type = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_half_day = serializers.BooleanField(default=False)
    reason = serializers.CharField()
    contact_address = serializers.CharField(required=False, allow_blank=True, default="")
    substitute_employee_id = serializers.IntegerField(
        required=False, allow_null=True, default=None
    )


class ReviewLeaveInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    review_comment = serializers.CharField(required=False, allow_blank=True, default="")
