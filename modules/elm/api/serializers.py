from rest_framework import serializers

from modules.elm.models import (
    LeaveApprovalTask,
    LeaveBalanceEvent,
    LeaveRequest,
    LeaveRequestEvent,
)


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = (
            "id",
            "substitute_user_id",
            "substitute_status",
            "substitute_replacement_count",
            "leave_type_code",
            "requested_start_date",
            "requested_end_date",
            "day_part",
            "total_days",
            "status",
            "submitted_at",
            "updated_at",
            "approved_at",
            "rejection_reason",
        )
        read_only_fields = fields


class LeaveRequestSubmissionSerializer(serializers.Serializer):
    leave_type_code = serializers.ChoiceField(
        choices=LeaveRequest.LEAVE_CHOICES
    )
    requested_start_date = serializers.DateField()
    requested_end_date = serializers.DateField()
    substitute_user_id = serializers.IntegerField(min_value=1)
    day_part = serializers.ChoiceField(
        choices=LeaveRequest.DAY_PART_CHOICES,
        default="FULL",
    )


class LeaveSubstituteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=("ACCEPT", "DECLINE"))


class LeaveSubstituteReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField(min_value=1)


class LeaveApprovalDecisionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(
        choices=(
            "RECOMMEND",
            "NOT_RECOMMENDED",
            "VERIFY",
            "APPROVE",
            "REJECT",
        )
    )
    reason = serializers.CharField(
        max_length=2000,
        required=False,
        allow_blank=True,
        default="",
    )


class LeaveRequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestEvent
        fields = (
            "id",
            "event_type",
            "from_status",
            "to_status",
            "actor_user_id",
            "note",
            "created_at",
        )
        read_only_fields = fields


class LeaveApprovalTaskSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)

    class Meta:
        model = LeaveApprovalTask
        fields = (
            "id",
            "request",
            "step_order",
            "stage",
            "decision_mode",
            "status",
            "assigned_at",
        )
        read_only_fields = fields


class LeaveBalanceSummarySerializer(serializers.Serializer):
    leave_type_code = serializers.CharField()
    year = serializers.IntegerField()
    annual_entitlement = serializers.DecimalField(
        max_digits=7, decimal_places=2, allow_null=True
    )
    opening_balance = serializers.DecimalField(max_digits=8, decimal_places=2)
    annual_credit = serializers.DecimalField(max_digits=8, decimal_places=2)
    used_days = serializers.DecimalField(max_digits=8, decimal_places=2)
    reserved_days = serializers.DecimalField(max_digits=8, decimal_places=2)
    available_days = serializers.DecimalField(max_digits=9, decimal_places=2)
    carries_forward = serializers.BooleanField()


class LeaveBalanceEventSerializer(serializers.ModelSerializer):
    leave_type_code = serializers.CharField(source="balance.leave_type_code")
    year = serializers.IntegerField(source="balance.year")

    class Meta:
        model = LeaveBalanceEvent
        fields = (
            "id",
            "leave_type_code",
            "year",
            "event_type",
            "amount",
            "note",
            "created_at",
        )
        read_only_fields = fields
