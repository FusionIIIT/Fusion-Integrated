"""Serializers.

Read and write are deliberately separate shapes: what comes back carries the
workflow history a person needs to see, and what goes in carries only what they
may set. Anything that would let a caller set a status, a balance or a routing
decision from the outside is simply not a field here.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain import categories as cat
from modules.leave.models import (
    CalendarEntry,
    LeaveApproval,
    LeaveBalance,
    LeaveCalendar,
    LeavePolicy,
    LeaveRequest,
)


class HalfDayField(serializers.CharField):
    def to_internal_value(self, value):
        if value in (None, ""):
            return ""
        value = str(value).lower()
        if value not in cat.HALVES:
            raise serializers.ValidationError(
                "A half day is either 'first' or 'second'.")
        return value


class LeaveRequestSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display",
                                           read_only=True)
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)
    half = HalfDayField(required=False)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "kind", "kind_label", "category", "category_label",
            "from_date", "to_date", "half", "days", "purpose", "status",
            "station_leave_required", "station_leave_details", "parent",
            "unit_head_user_id", "final_authority", "establishment_first",
            "self_sanction", "substitute_user_id", "substitute_response",
            "is_offline", "sanction_reference", "sanctioned_on",
            "decision", "decision_remarks", "decided_at", "created_at",
        ]
        read_only_fields = [
            "days", "status", "substitute_response", "is_offline",
            "sanction_reference", "sanctioned_on", "decision",
            "decision_remarks", "decided_at", "unit_head_user_id",
            "final_authority", "establishment_first", "self_sanction",
        ]


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=list(cat.CATEGORIES))
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    half = HalfDayField(required=False)
    purpose = serializers.CharField(max_length=1000)
    station_leave_required = serializers.BooleanField(default=False)
    station_leave_details = serializers.CharField(max_length=300,
                                                  required=False, allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    substitute_required = serializers.BooleanField(default=False)

    def validate(self, attrs):
        # Station Leave details belong inside the same application (BR-EL-013),
        # so the pair is checked as one thing.
        if attrs.get("station_leave_required") and not (
                attrs.get("station_leave_details") or "").strip():
            raise serializers.ValidationError(
                {"station_leave_details":
                 "Describe the Station Leave: where you are going, and when."})
        return attrs


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(
        choices=["approve", "reject", "recommended", "not_recommended"])
    remarks = serializers.CharField(max_length=300, required=False,
                                    allow_blank=True)


class RouteSerializer(serializers.Serializer):
    remarks = serializers.CharField(max_length=300, required=False,
                                    allow_blank=True)


class LeaveWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=300, required=False,
                                    allow_blank=True)


class CancellationSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=1000)


class ExtensionSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    substitute_required = serializers.BooleanField(default=False)
    purpose = serializers.CharField(max_length=1000, required=False,
                                    allow_blank=True)


class ResumptionSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(max_length=1000, required=False,
                                    allow_blank=True)


class ResumptionReviewSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["normal", "early", "late"])
    remarks = serializers.CharField(max_length=300, required=False,
                                    allow_blank=True)


class ReplacementSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class BalanceSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display",
                                           read_only=True)

    class Meta:
        model = LeaveBalance
        fields = ["category", "category_label", "opening", "credited", "used",
                  "available"]


class ApprovalSerializer(serializers.ModelSerializer):
    stage_label = serializers.CharField(source="get_stage_display",
                                        read_only=True)

    class Meta:
        model = LeaveApproval
        fields = ["id", "stage", "stage_label", "decision", "actor_user_id",
                  "remarks", "created_at"]


# -- configuration ------------------------------------------------------------
class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = [
            "id", "label", "year_label", "starts_on", "ends_on",
            "cl_days", "rh_days", "scl_days", "el_days", "vl_days",
            "col_days", "vl_per_el", "authority_path",
            "establishment_designation", "establishment_step_enabled",
            "reminder_hours", "escalation_hours", "year_end_on",
        ]


class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ["id", "date", "ends_on", "kind", "label"]


class CalendarSerializer(serializers.ModelSerializer):
    entries = CalendarEntrySerializer(many=True, read_only=True)

    class Meta:
        model = LeaveCalendar
        fields = ["id", "year_label", "label", "published_at", "entries"]


class CalendarWriteSerializer(serializers.Serializer):
    year_label = serializers.CharField(max_length=9)
    label = serializers.CharField(max_length=120, required=False, allow_blank=True)
    entries = CalendarEntrySerializer(many=True)

    def validate_entries(self, value):
        from modules.leave.services import calendar as calendar_service

        return calendar_service._validate_entries(value)


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=list(cat.CATEGORIES))
    from_date = serializers.DateField()
    to_date = serializers.DateField()
    sanctioned_on = serializers.DateField()
    sanction_reference = serializers.CharField(max_length=120)
    reason = serializers.CharField(max_length=300)
