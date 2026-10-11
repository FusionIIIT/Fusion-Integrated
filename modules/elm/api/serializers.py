"""Serializers. Thin, and every write serializer is an explicit allow-list.

`fields = "__all__"` is never used here — it is exactly how `user_id`, `status`
or `days` ends up writable by whoever posts the right JSON.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.elm.domain import state_machine as sm
from modules.elm.models import Holiday, LeaveApplication, LeaveEvent, LeaveType


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = ("id", "code", "name", "annual_entitlement_days",
                  "counts_calendar_days", "allows_half_day", "requires_reason",
                  "effective_from", "is_active")
        read_only_fields = fields


class LeaveTypeWriteSerializer(serializers.Serializer):
    code = serializers.CharField(max_length=12)
    name = serializers.CharField(max_length=60)
    annual_entitlement_days = serializers.DecimalField(max_digits=5,
                                                       decimal_places=1,
                                                       min_value=0, required=False,
                                                       default=0)
    counts_calendar_days = serializers.BooleanField(required=False, default=False)
    allows_half_day = serializers.BooleanField(required=False, default=False)
    requires_reason = serializers.BooleanField(required=False, default=False)
    effective_from = serializers.DateField(required=False, allow_null=True,
                                           default=None)


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ("id", "date", "name")
        read_only_fields = fields


class HolidayWriteSerializer(serializers.Serializer):
    date = serializers.DateField()
    name = serializers.CharField(max_length=80)


class LeaveEventSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source="actor_label", read_only=True)

    class Meta:
        model = LeaveEvent
        fields = ("id", "from_status", "to_status", "actor_user_id", "actor_name",
                  "note", "at")
        read_only_fields = fields


class LeaveApplicationSerializer(serializers.ModelSerializer):
    leave_type = LeaveTypeSerializer(read_only=True)
    applicant_name = serializers.SerializerMethodField()
    allowed_transitions = serializers.SerializerMethodField()

    class Meta:
        model = LeaveApplication
        fields = ("id", "user_id", "applicant_name", "leave_type", "start_date",
                  "end_date", "days", "is_half_day", "half_day_part", "reason",
                  "status", "decided_by_user_id", "decided_at", "decision_note",
                  "allowed_transitions", "created_at")
        read_only_fields = fields

    def get_applicant_name(self, application: LeaveApplication) -> str:
        # The view batches the directory lookup into the context, so this is
        # a dict read, never a request per row.
        people = self.context.get("people") or {}
        person = people.get(application.user_id)
        return getattr(person, "display_name", "") if person else ""

    def get_allowed_transitions(self, application: LeaveApplication) -> list[str]:
        """State machine *and* permission, so a control is never rendered for
        an action the server would refuse (Step 6.4)."""
        actor = self.context.get("actor")
        if actor is None:
            return []
        from modules.elm.services.applications import actor_lanes
        allowed = set()
        for lane in actor_lanes(actor, application):
            for target in sm.allowed_targets(application.status, lane):
                edge = sm.resolve(application.status, target, lane)
                if actor.has_permission(edge.permission):
                    allowed.add(target)
        return sorted(allowed)


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_type_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    is_half_day = serializers.BooleanField(required=False, default=False)
    half_day_part = serializers.ChoiceField(choices=LeaveApplication.HALF_DAY_PARTS,
                                            required=False, allow_blank=True,
                                            default="")
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                   default="")


class LeaveTransitionSerializer(serializers.Serializer):
    """Named for this module: a bare `TransitionSerializer` collides with
    placement's in the generated schema (drf-spectacular derives component
    names from class names alone)."""

    # sorted(): ALL_STATUSES is a frozenset, so list() order would change per
    # run and churn the generated schema, which CI diffs byte for byte.
    to_status = serializers.ChoiceField(choices=sorted(sm.ALL_STATUSES))
    note = serializers.CharField(max_length=300, required=False, allow_blank=True,
                                 default="")


class BalanceSerializer(serializers.Serializer):
    """Reads selectors.queries.Balance, which is a dataclass, not a model."""

    user_id = serializers.IntegerField()
    leave_type_code = serializers.CharField()
    leave_type_name = serializers.CharField()
    entitled_days = serializers.DecimalField(max_digits=6, decimal_places=1)
    used_days = serializers.DecimalField(max_digits=6, decimal_places=1)
    available_days = serializers.DecimalField(max_digits=6, decimal_places=1)


class BalanceAdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    leave_type_id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    days = serializers.DecimalField(max_digits=5, decimal_places=1)
    note = serializers.CharField(max_length=300)
