"""Serializers for leave module."""

from __future__ import annotations

from rest_framework import serializers

from modules.leave.models import (
    AuthorityRule,
    Calendar,
    CategoryRule,
    Holiday,
    LeaveRequest,
    LeaveTransition,
    LedgerEntry,
    Policy,
    SlaRule,
    VacationPeriod,
)


class StationSerializer(serializers.Serializer):
    destination = serializers.CharField(required=True)
    from_date = serializers.DateField(required=False)
    to_date = serializers.DateField(required=False)


class ApplyLeaveSerializer(serializers.Serializer):
    category = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField()
    half = serializers.CharField(default="none", required=False)
    evidence_reference = serializers.CharField(default="", required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station = StationSerializer(required=False, allow_null=True)


class DecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class RemarkSerializer(serializers.Serializer):
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class RenominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class SubstituteResponseSerializer(serializers.Serializer):
    accepted = serializers.BooleanField()
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSerializer(serializers.Serializer):
    resumed_on = serializers.DateField()
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class ExtensionSerializer(serializers.Serializer):
    new_end = serializers.DateField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    remark = serializers.CharField(required=False, allow_blank=True, default="")


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.CharField()
    starts_on = serializers.DateField()
    ends_on = serializers.DateField()
    reason = serializers.CharField()
    half = serializers.CharField(default="none", required=False)
    faculty = serializers.BooleanField(default=True)
    unit = serializers.CharField(required=False, allow_blank=True, default="")
    note = serializers.CharField(required=False, allow_blank=True, default="")


class LeaveRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequest
        fields = [
            "id",
            "user_id",
            "category",
            "state",
            "starts_on",
            "ends_on",
            "half",
            "reason",
            "evidence_reference",
            "requested_days",
            "actual_days",
            "station_leave",
            "station_destination",
            "substitute_user_id",
            "extension_to",
            "unit_head_recommended",
            "sanctioning_designation",
            "resumed_on",
            "decided_at",
            "created_at",
        ]


class LeaveTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = [
            "id",
            "from_state",
            "to_state",
            "event",
            "actor_role",
            "actor_user_id",
            "remark",
            "workflow_ref",
            "created_at",
        ]


class LedgerEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = LedgerEntry
        fields = [
            "id",
            "year",
            "category",
            "days",
            "reason",
            "request_id",
            "note",
            "created_at",
        ]


class BalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    available = serializers.DecimalField(max_digits=5, decimal_places=2)
    credited = serializers.DecimalField(max_digits=5, decimal_places=2)
    consumed = serializers.DecimalField(max_digits=5, decimal_places=2)
    restored = serializers.DecimalField(max_digits=5, decimal_places=2)


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            "id",
            "version",
            "effective_from",
            "effective_to",
            "published",
            "note",
            "vl_to_el_ratio",
            "vl_to_el_rounding",
            "early_return_tail",
            "max_backdate_days",
        ]


class DraftPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = Policy
        fields = [
            "version",
            "effective_from",
            "note",
            "vl_to_el_ratio",
            "vl_to_el_rounding",
            "early_return_tail",
            "max_backdate_days",
        ]


class CategoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRule
        fields = [
            "id",
            "category",
            "annual_credit",
            "carries_forward",
            "carry_forward_cap",
            "applies_to_faculty",
            "requires_evidence",
        ]


class DraftCategoryRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryRule
        fields = [
            "category",
            "annual_credit",
            "carries_forward",
            "carry_forward_cap",
            "applies_to_faculty",
            "requires_evidence",
        ]


class AuthorityRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorityRule
        fields = [
            "id",
            "category",
            "unit",
            "designation",
            "applies_to_faculty",
            "establishment_step",
            "sanctioning_designation",
            "self_sanction",
            "specificity",
        ]


class SlaRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaRule
        fields = [
            "id",
            "state",
            "remind_after_hours",
            "escalate_after_hours",
            "escalate_to_designation",
        ]


class PolicyGapSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    gaps = serializers.ListField(child=serializers.CharField())


class CalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = ["id", "year", "version", "published"]


class DraftCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Calendar
        fields = ["year", "version"]


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["id", "day", "name", "restricted"]


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "name", "starts_on", "ends_on"]
