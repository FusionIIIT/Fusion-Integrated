"""Serializers. Thin, and every write serializer is an explicit allow-list.

`fields = "__all__"` is never used here — it is exactly how `user_id`,
`status` or `chargeable_days` ends up writable by whoever posts the right
JSON.
"""
from __future__ import annotations

from rest_framework import serializers

from modules.leave.domain.categories import CATEGORIES, HALF_DAY_CHOICES
from modules.leave.models import (
    AuthorityAssignment,
    LeaveBalance,
    LeaveNotification,
    LeavePolicy,
    LeaveRequest,
    LeaveRequestEvent,
    LeaveResumption,
    OrganizationalUnit,
    SlaThreshold,
)
from modules.leave.selectors import actions

CATEGORY_CHOICES = [(c, c) for c in CATEGORIES]


# -- requests ---------------------------------------------------------------
class LeaveEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveRequestEvent
        fields = ("id", "from_status", "to_status", "kind", "actor_user_id",
                  "actor_label", "note", "at")
        read_only_fields = fields


class LeaveResumptionSerializer(serializers.ModelSerializer):
    adjustment_days = serializers.SerializerMethodField()

    class Meta:
        model = LeaveResumption
        fields = ("id", "request", "actual_date", "details", "status",
                  "approved_end_date", "adjustment_days",
                  "reviewed_by_user_id", "reviewed_at", "review_note",
                  "created_at")
        read_only_fields = fields

    def get_adjustment_days(self, obj) -> str:
        # "-1", not "-1.00": a day count reads as days, not as money.
        from decimal import Decimal
        value = Decimal(str(obj.adjustment_days))
        return str(int(value)) if value == value.to_integral_value() \
            else str(value)


class LeaveRequestSerializer(serializers.ModelSerializer):
    """One file as any actor sees it. Names come batched through the view's
    context, so a list costs one directory call, not one per row."""

    applicant_name = serializers.SerializerMethodField()
    substitute_name = serializers.SerializerMethodField()
    allowed_actions = serializers.SerializerMethodField()
    is_pending = serializers.BooleanField(read_only=True)
    pending_resumption = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = (
            "id", "user_id", "applicant_name", "kind", "source", "category",
            "status",
            "start_date", "end_date", "half_day", "purpose", "evidence_note",
            "station_leave", "station_place", "station_reason",
            "chargeable_days", "year", "base_request",
            "substitute_user_id", "substitute_name", "substitute_status",
            "unit_head_user_id", "unit_head_outcome", "unit_head_note",
            "establishment_user_id", "authority_user_id",
            "is_director_self_sanction",
            "decision", "decided_at", "decided_by_user_id", "decision_note",
            "sanction_reference",
            "task_class", "task_user_id", "task_assigned_at",
            "reminder_sent_at", "escalated_at",
            "actual_end_date", "admin_note",
            "allowed_actions", "is_pending", "pending_resumption",
            "created_at", "updated_at",
        )
        read_only_fields = fields

    def _people(self) -> dict:
        return self.context.get("people", {})

    def get_applicant_name(self, obj) -> str:
        person = self._people().get(obj.user_id)
        return person.display_name if person else ""

    def get_substitute_name(self, obj) -> str:
        person = self._people().get(obj.substitute_user_id)
        return person.display_name if person else ""

    def get_allowed_actions(self, obj) -> list[str]:
        actor = self.context.get("actor")
        return actions.allowed_actions(obj, actor)

    def get_pending_resumption(self, obj):
        row = obj.resumptions.filter(
            status=LeaveResumption.PENDING).order_by("-created_at").first()
        if row is None:
            return None
        return LeaveResumptionSerializer(row).data


class SubmitSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=list(HALF_DAY_CHOICES),
                                       default="none")
    purpose = serializers.CharField(required=False, allow_blank=True,
                                    default="")
    evidence_note = serializers.CharField(required=False, allow_blank=True,
                                          default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_place = serializers.CharField(required=False, allow_blank=True,
                                          default="")
    station_reason = serializers.CharField(required=False, allow_blank=True,
                                           default="")
    substitute_user_id = serializers.IntegerField(required=False,
                                                  allow_null=True,
                                                  default=None)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True,
                                   default="")


class ExtensionSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(required=False, allow_blank=True,
                                   default="")
    substitute_user_id = serializers.IntegerField(required=False,
                                                  allow_null=True,
                                                  default=None)


class ResumptionFileSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    details = serializers.CharField(required=False, allow_blank=True,
                                    default="")


class ReviewSerializer(serializers.Serializer):
    """Unit Head review: both vocabularies, narrowed by the service to what
    this desk and category actually accept."""
    outcome = serializers.ChoiceField(choices=(
        ("approve", "approve"), ("reject", "reject"),
        ("recommended", "recommended"), ("not_recommended", "not_recommended")))
    note = serializers.CharField(required=False, allow_blank=True, default="")
    reference = serializers.CharField(required=False, allow_blank=True,
                                      default="")


class SanctionSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=(
        ("approve", "approve"), ("reject", "reject")))
    note = serializers.CharField(required=False, allow_blank=True, default="")
    reference = serializers.CharField(required=False, allow_blank=True,
                                      default="")


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteRespondSerializer(serializers.Serializer):
    response = serializers.ChoiceField(choices=(
        ("accept", "accept"), ("decline", "decline")))


class NominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ResumptionReviewSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, default="")


# -- balances, notifications ------------------------------------------------
class BalanceSerializer(serializers.ModelSerializer):
    available = serializers.SerializerMethodField()

    class Meta:
        model = LeaveBalance
        fields = ("id", "user_id", "category", "year", "carried_forward",
                  "credited", "used", "adjusted", "available")
        read_only_fields = fields

    def get_available(self, obj) -> float:
        return float(obj.available)


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = ("id", "kind", "message", "request", "read_at", "created_at")
        read_only_fields = fields


class MarkReadSerializer(serializers.Serializer):
    ids = serializers.ListField(child=serializers.IntegerField(),
                                required=False, default=list)


# -- administration ---------------------------------------------------------
class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ("id", "cl_annual", "rh_annual", "scl_annual",
                  "el_annual_nonfaculty", "el_annual_faculty", "col_annual",
                  "vl_annual_faculty", "vl_to_el_numerator",
                  "vl_to_el_denominator", "el_carry_forward",
                  "col_carry_forward", "substitute_required_categories",
                  "scl_evidence_required", "col_evidence_required",
                  "year_end_month", "year_end_day", "updated_at")
        read_only_fields = ("id", "updated_at")


class HolidayItemSerializer(serializers.Serializer):
    date = serializers.DateField()
    name = serializers.CharField(max_length=120, required=False,
                                 allow_blank=True, default="")
    kind = serializers.ChoiceField(choices=(("closed", "closed"),
                                            ("restricted", "restricted")),
                                   default="closed")


class CalendarWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=120)
    academic_year = serializers.CharField(max_length=20, required=False,
                                          allow_blank=True, default="")
    holidays = HolidayItemSerializer(many=True, required=False,
                                     default=list)
    publish = serializers.BooleanField(required=False, default=False)


class VacationWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True,
                                  default=None)
    name = serializers.CharField(max_length=120)
    academic_year = serializers.CharField(max_length=20, required=False,
                                          allow_blank=True, default="")
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    source_ref = serializers.CharField(max_length=200, required=False,
                                       allow_blank=True, default="")


class OrgUnitSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrganizationalUnit
        fields = ("id", "code", "name", "kind", "head_user_id", "created_at")
        read_only_fields = ("id", "created_at")


class OrgUnitWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True,
                                  default=None)
    code = serializers.CharField(max_length=80)
    name = serializers.CharField(max_length=160, required=False,
                                 allow_blank=True, default="")
    kind = serializers.ChoiceField(choices=(("department", "department"),
                                            ("section", "section"),
                                            ("office", "office")),
                                   default="department")
    head_user_id = serializers.IntegerField(required=False, allow_null=True,
                                            default=None)


class AuthoritySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuthorityAssignment
        fields = ("id", "role_code", "user_id", "org_unit", "categories")
        read_only_fields = ("id",)


class AuthorityWriteSerializer(serializers.Serializer):
    id = serializers.IntegerField(required=False, allow_null=True,
                                  default=None)
    role_code = serializers.ChoiceField(choices=(
        ("establishment", "establishment"), ("dean", "dean"),
        ("registrar", "registrar"), ("director", "director")))
    user_id = serializers.IntegerField()
    org_unit_id = serializers.IntegerField(required=False, allow_null=True,
                                           default=None)
    categories = serializers.ListField(child=serializers.CharField(),
                                       required=False, default=list)


class SlaThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = SlaThreshold
        fields = ("id", "task_class", "reminder_hours", "escalation_hours",
                  "escalation_user_id")
        read_only_fields = ("id",)


class SlaWriteItemSerializer(serializers.Serializer):
    task_class = serializers.ChoiceField(choices=SlaThreshold.TASK_CLASS)
    reminder_hours = serializers.IntegerField(required=False, allow_null=True,
                                              default=None)
    escalation_hours = serializers.IntegerField(required=False,
                                                allow_null=True, default=None)
    escalation_user_id = serializers.IntegerField(required=False,
                                                  allow_null=True,
                                                  default=None)


class SlaWriteSerializer(serializers.Serializer):
    thresholds = SlaWriteItemSerializer(many=True)


class OfflineLeaveSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day = serializers.ChoiceField(choices=list(HALF_DAY_CHOICES),
                                       default="none")
    purpose = serializers.CharField(required=False, allow_blank=True,
                                    default="")
    sanction_reference = serializers.CharField(max_length=200, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class AdjustBalanceSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORY_CHOICES)
    year = serializers.IntegerField()
    days = serializers.DecimalField(max_digits=6, decimal_places=2)
    note = serializers.CharField(max_length=300, required=False,
                                 allow_blank=True, default="")


class AnnotateSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=1000)
