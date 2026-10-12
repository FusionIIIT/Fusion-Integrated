from __future__ import annotations

from rest_framework import serializers

from modules.elm.domain import categories as c
from modules.elm.domain import state_machine as sm
from modules.elm.models import (
    CalendarEntry,
    CalendarVersion,
    LeaveRequest,
    LeaveTransition,
    LedgerEntry,
    Notification,
    OfflineLeaveRecord,
    PolicyVersion,
)

CATEGORY_CHOICES = [(k, v) for k, v in c.LABELS.items()]


def _name(ctx, uid):
    if uid is None:
        return ""
    u = (ctx.get("names") or {}).get(uid)
    return u.display_name if u else ""


class LeaveRequestSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    applicant_name = serializers.SerializerMethodField()
    substitute_name = serializers.SerializerMethodField()
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)
    allowed_decisions = serializers.SerializerMethodField()
    status = serializers.CharField(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = [
            "id", "kind", "parent_id", "user_id", "applicant_name", "applicant_kind",
            "applicant_unit", "category", "category_label", "start_date", "end_date",
            "half", "days", "purpose", "medical_evidence", "station_leave",
            "station_from", "station_to", "station_address", "substitute_user_id",
            "substitute_name", "substitute_status", "responsibility", "status", "route",
            "stage", "current_role", "recommendation", "decision_note", "decided_at",
            "actual_return_date", "resumption_note", "allowed_decisions", "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_category_label(self, obj) -> str:
        return c.LABELS.get(obj.category, obj.category)

    def get_applicant_name(self, obj) -> str:
        return _name(self.context, obj.user_id)

    def get_substitute_name(self, obj) -> str:
        return _name(self.context, obj.substitute_user_id)

    def get_allowed_decisions(self, obj) -> list[str]:
        if not self.context.get("queue"):
            return []
        step = obj.current_step
        if step is None:
            return []
        return list(sm.decision_events(step["step"], obj.category in c.UNIT_HEAD_FINAL,
                                       obj.status == sm.CANCELLATION_PENDING))


class LeaveInputSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["", *c.HALVES], required=False, default="")
    purpose = serializers.CharField(max_length=2000)
    medical_evidence = serializers.CharField(max_length=500, required=False, default="",
                                             allow_blank=True)
    station_leave = serializers.BooleanField(required=False, default=False)
    station_from = serializers.DateField(required=False, allow_null=True, default=None)
    station_to = serializers.DateField(required=False, allow_null=True, default=None)
    station_address = serializers.CharField(max_length=300, required=False, default="",
                                            allow_blank=True)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)
    responsibility = serializers.CharField(max_length=300, required=False, default="",
                                           allow_blank=True)


class ExtensionSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                  default=None)
    responsibility = serializers.CharField(max_length=300, required=False, default="",
                                           allow_blank=True)


class RenominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()
    responsibility = serializers.CharField(max_length=300, required=False, default="",
                                           allow_blank=True)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, default="",
                                   allow_blank=True)


class DecisionSerializer(serializers.Serializer):
    event = serializers.ChoiceField(choices=[
        sm.APPROVE, sm.REJECT, sm.RECOMMEND, sm.NOT_RECOMMEND, sm.FORWARD,
        sm.CANCEL_ADVANCE, sm.CANCEL_APPROVE, sm.CANCEL_REJECT])
    note = serializers.CharField(max_length=500, required=False, default="",
                                 allow_blank=True)


class SubstituteResponseSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, default="",
                                 allow_blank=True)


class ResumptionSerializer(serializers.Serializer):
    actual_return_date = serializers.DateField()
    note = serializers.CharField(max_length=500, required=False, default="",
                                 allow_blank=True)


class VerifySerializer(serializers.Serializer):
    verified = serializers.BooleanField()
    note = serializers.CharField(max_length=500, required=False, default="",
                                 allow_blank=True)


class TransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = ["from_status", "to_status", "event", "actor_role", "note", "at"]


class LedgerEntrySerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = LedgerEntry
        fields = ["id", "category", "entry_type", "delta", "year", "request_id",
                  "note", "at"]


class BalanceSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    balances = serializers.DictField(child=serializers.DecimalField(
        max_digits=7, decimal_places=2))
    pending = serializers.DictField(child=serializers.DecimalField(
        max_digits=7, decimal_places=2))
    history = LedgerEntrySerializer(many=True)


class PolicyVersionSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = PolicyVersion
        fields = ["id", "name", "params", "hierarchy", "effective_from", "status",
                  "published_at", "created_at"]
        read_only_fields = ["id", "status", "published_at", "created_at"]


class CalendarEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = CalendarEntry
        fields = ["kind", "name", "start_date", "end_date"]


class CalendarVersionSerializer(serializers.ModelSerializer):
    entries = CalendarEntrySerializer(many=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = CalendarVersion
        fields = ["id", "name", "effective_from", "status", "published_at", "entries",
                  "created_at"]
        read_only_fields = ["id", "status", "published_at", "created_at"]


class OfflineInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=["", *c.HALVES], required=False, default="")
    purpose = serializers.CharField(max_length=2000, required=False, default="",
                                    allow_blank=True)
    sanction_reference = serializers.CharField(max_length=120)
    sanctioned_by = serializers.CharField(max_length=120)
    sanctioned_on = serializers.DateField()
    evidence_note = serializers.CharField(max_length=500, required=False, default="",
                                          allow_blank=True)


class OfflineRecordSerializer(serializers.ModelSerializer):
    leave = LeaveRequestSerializer(source="request", read_only=True)

    class Meta:
        model = OfflineLeaveRecord
        fields = ["id", "sanction_reference", "sanctioned_by", "sanctioned_on",
                  "evidence_note", "recorded_by_user_id", "created_at", "leave"]


class NotificationSerializer(serializers.ModelSerializer):
    request_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = Notification
        fields = ["id", "message", "request_id", "created_at", "read_at"]
