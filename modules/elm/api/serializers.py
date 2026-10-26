from rest_framework import serializers

from modules.elm.models import (
    LeaveApproval,
    LeaveAuditEvent,
    LeaveBalance,
    LeaveRequest,
    RestrictedHoliday,
)


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = "__all__"
        read_only_fields = (
            "employee_id",
            "status",
            "approval_stage",
            "substitute_accepted",
            "final_approver_id",
            "final_approved_at",
            "created_at",
            "updated_at",
        )

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


class LeaveApprovalSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApproval
        fields = "__all__"
        read_only_fields = fields


class LeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.ReadOnlyField()

    class Meta:
        model = LeaveBalance
        fields = "__all__"
        read_only_fields = fields


class RestrictedHolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = RestrictedHoliday
        fields = "__all__"
        read_only_fields = ("published_at",)


class LeaveAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveAuditEvent
        fields = "__all__"
        read_only_fields = fields
