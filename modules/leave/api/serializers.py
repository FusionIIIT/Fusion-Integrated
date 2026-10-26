"""DRF serializers for Employee Leave Management (ELM) API."""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.models import (
    LeaveApplication,
    LeaveApplicationAudit,
    LeaveBalance,
    LeaveCategory,
)


class LeaveApplicationAuditSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveApplicationAudit
        fields = ("id", "application_id", "status", "reason", "at")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    chargeable_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = (
            "id",
            "user_id",
            "posting_id",
            "category",
            "start_date",
            "end_date",
            "reason",
            "half_day_cl",
            "substitute_id",
            "station_leave_details",
            "status",
            "chargeable_days",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_chargeable_days(self, obj) -> float:
        return obj.chargeable_days()


class LeaveApplicationCreateSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=LeaveCategory.choices)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    half_day_cl = serializers.BooleanField(required=False, default=False)
    substitute_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    station_leave_details = serializers.JSONField(required=False, default=dict)


class SubstituteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ReviewActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["recommend", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionActionSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveBalanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "year", "balance")
        read_only_fields = fields
