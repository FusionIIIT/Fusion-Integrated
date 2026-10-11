"""Serializers. Read serializers are explicit; write serializers are allow-lists."""
from rest_framework import serializers

from modules.elm.domain import policy
from modules.elm.models import (
    ApprovalStep,
    CategoryPolicy,
    Holiday,
    HolidayCalendar,
    LeaveRequest,
    LedgerEntry,
    Notification,
    RequestEvent,
    SanctionRoute,
    SlaPolicy,
    UnitHead,
    VacationPeriod,
)
from modules.elm.services.requests import OUTCOMES

CATEGORY = serializers.ChoiceField(choices=policy.CATEGORIES)


class RequestEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ("id", "actor_id", "actor_role", "from_state", "to_state", "note",
                  "created_at")


class ApprovalStepSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApprovalStep
        fields = ("id", "sequence", "stage", "assignee_id", "status", "outcome",
                  "remarks", "assigned_at", "acted_at")


class LeaveRequestSerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    assignee_id = serializers.IntegerField(read_only=True, allow_null=True)
    class Meta:
        model = LeaveRequest
        fields = ("id", "user_id", "kind", "source", "parent", "category",
                  "applicant_kind", "unit", "start_date", "end_date", "half",
                  "days", "purpose", "station_leave", "station_address",
                  "substitute_id", "is_director_applicant", "state", "assignee_id",
                  "recommendation", "decided_by_id", "decided_at",
                  "decision_remarks", "actual_resumption_date",
                  "offline_reference", "created_at")


class LeaveRequestDetailSerializer(LeaveRequestSerializer):
    events = RequestEventSerializer(many=True, read_only=True)
    steps = ApprovalStepSerializer(many=True, read_only=True)

    class Meta(LeaveRequestSerializer.Meta):
        fields = (*LeaveRequestSerializer.Meta.fields, "steps", "events")


class ApplySerializer(serializers.Serializer):
    category = CATEGORY
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=policy.HALVES, required=False,
                                   allow_null=True)
    purpose = serializers.CharField(max_length=2000, allow_blank=True,
                                    required=False, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_address = serializers.CharField(max_length=300, allow_blank=True,
                                            required=False, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class ExtendSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000, allow_blank=True,
                                    required=False, default="")
    substitute_id = serializers.IntegerField(required=False, allow_null=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=2000, allow_blank=True,
                                   required=False, default="")


class ResumeSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(max_length=2000, allow_blank=True,
                                    required=False, default="")


class SubstituteSerializer(serializers.Serializer):
    substitute_id = serializers.IntegerField()


class RespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()


class DecideSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=OUTCOMES)
    remarks = serializers.CharField(max_length=500, allow_blank=True,
                                    required=False, default="")


class BalanceSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    balances = serializers.DictField(child=serializers.DecimalField(
        max_digits=6, decimal_places=1))
    ledger = serializers.ListField(child=serializers.DictField())


class LedgerEntrySerializer(serializers.ModelSerializer):
    kind = serializers.CharField(read_only=True)
    class Meta:
        model = LedgerEntry
        fields = ("id", "category", "year", "kind", "days", "request", "note",
                  "created_at")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ("id", "request", "message", "read_at", "created_at")


class EmployeeSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    kind = serializers.CharField()
    department = serializers.CharField()


# -- administration -------------------------------------------------------------
class CategoryPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = CategoryPolicy
        fields = ("category", "annual_days", "updated_at")


class UnitHeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = UnitHead
        fields = ("id", "unit", "head_user_id")


class SanctionRouteSerializer(serializers.ModelSerializer):
    class Meta:
        model = SanctionRoute
        fields = ("id", "category", "applicant_kind", "establishment_user_id",
                  "authority_user_id")


class SlaPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaPolicy
        fields = ("id", "reminder_hours", "escalation_hours",
                  "escalation_user_id", "created_at")


class HolidaySerializer(serializers.ModelSerializer):
    kind = serializers.ChoiceField(choices=["closed", "restricted"])
    class Meta:
        model = Holiday
        fields = ("id", "date", "name", "kind")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ("id", "year", "status", "published_at", "holidays")


class CalendarCreateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class VacationPeriodSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ("id", "label", "start_date", "end_date")


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = CATEGORY
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=policy.HALVES, required=False,
                                   allow_null=True)
    reference = serializers.CharField(max_length=200)
    purpose = serializers.CharField(max_length=2000, allow_blank=True,
                                    required=False, default="")


class AdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = CATEGORY
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    days = serializers.DecimalField(max_digits=6, decimal_places=1)
    note = serializers.CharField(max_length=300)
