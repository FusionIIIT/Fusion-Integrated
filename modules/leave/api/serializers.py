"""Serializers for Leave Management endpoints."""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain.entities import ApprovalOutcome, LeaveType
from modules.leave.models import ApprovalDecision, LeaveBalance, LeaveRequest


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = [
            "id",
            "user_id",
            "leave_type",
            "year",
            "total_entitlement",
            "consumed_days",
            "available_balance",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ApprovalDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalDecision
        fields = [
            "id",
            "request_id",
            "authority_id",
            "next_authority_id",
            "outcome",
            "remarks",
            "decided_at",
        ]
        read_only_fields = fields


class LeaveRequestSerializer(serializers.ModelSerializer):
    decisions = ApprovalDecisionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "leave_type",
            "start_date",
            "end_date",
            "duration_days",
            "justification",
            "status",
            "current_authority_id",
            "current_authority_role",
            "forward_count",
            "cancellation_reason",
            "submission_date",
            "decisions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubmitLeaveRequestInputSerializer(serializers.Serializer):
    leave_type = serializers.ChoiceField(choices=[(t.value, t.name) for t in LeaveType])
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    duration_days = serializers.DecimalField(max_digits=5, decimal_places=1, min_value=0.5)
    justification = serializers.CharField(min_length=3, max_length=1000)


class DecideLeaveRequestInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=[
            (ApprovalOutcome.APPROVED.value, "Approved"),
            (ApprovalOutcome.REJECTED.value, "Rejected"),
            (ApprovalOutcome.FORWARDED.value, "Forwarded"),
        ]
    )
    remarks = serializers.CharField(max_length=1000, required=False, allow_blank=True)
    next_authority_id = serializers.IntegerField(required=False, allow_null=True)


class CancelLeaveRequestInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
