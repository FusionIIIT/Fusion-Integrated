from rest_framework import serializers

from modules.leave.domain.categories import Category
from modules.leave.domain.counting import Half
from modules.leave.domain.workflow import PENDING, Decision
from modules.leave.models import (
    AuthorityRule,
    HolidayCalendar,
    LeaveNotification,
    LeavePolicy,
    LeaveRequest,
    LeaveTransition,
    OrgUnit,
    Resumption,
    SlaPolicy,
    VacationPeriod,
)

CATEGORIES = [c.value for c in Category]


class LeaveTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveTransition
        fields = ["from_status", "to_status", "event", "actor_user_id", "note", "at"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    applicant_name = serializers.SerializerMethodField()
    source = serializers.CharField(read_only=True)
    kind = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)
    category = serializers.CharField(read_only=True)
    half = serializers.CharField(read_only=True)
    resumption_status = serializers.SerializerMethodField()

    class Meta:
        model = LeaveRequest
        fields = ["id", "user_id", "applicant_name", "kind", "parent", "category",
                  "start_date", "end_date", "half", "days", "purpose", "station_leave",
                  "station_address", "medical_evidence_ref", "status", "substitute_user_id",
                  "unit_head_user_id", "establishment_user_id", "sanctioning_user_id",
                  "unit_head_final", "director_self", "recommendation", "source",
                  "offline_reference", "created_at", "decided_at", "resumption_status"]

    def get_applicant_name(self, obj) -> str:
        return self.context.get("names", {}).get(obj.user_id, "")

    def get_resumption_status(self, obj) -> str:
        r = getattr(obj, "resumption", None) if obj.kind == "new" else None
        return r.status if r else ""


class LeaveRequestDetailSerializer(LeaveRequestSerializer):
    transitions = LeaveTransitionSerializer(many=True, read_only=True)

    class Meta(LeaveRequestSerializer.Meta):
        fields = [*LeaveRequestSerializer.Meta.fields, "transitions"]


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=[h.value for h in Half], default=Half.FULL.value)
    purpose = serializers.CharField(max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)
    station_leave = serializers.BooleanField(default=False)
    station_address = serializers.CharField(max_length=255, required=False, allow_blank=True,
                                            default="")
    medical_evidence_ref = serializers.CharField(max_length=255, required=False,
                                                 allow_blank=True, default="")


class NoteSerializer(serializers.Serializer):
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(NoteSerializer):
    accept = serializers.BooleanField()


class RenominateSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ReviewSerializer(NoteSerializer):
    decision = serializers.ChoiceField(choices=[d.value for d in Decision])


class FinalDecisionSerializer(NoteSerializer):
    approve = serializers.BooleanField()


class ExtensionSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True)


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                    default="")


class ResumptionSerializer(serializers.ModelSerializer):
    leave = LeaveRequestSerializer(read_only=True)

    class Meta:
        model = Resumption
        fields = ["id", "leave", "actual_date", "remarks", "status", "outcome",
                  "adjustment_days", "reviewed_at"]


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveNotification
        fields = ["id", "kind", "message", "request", "read", "created_at"]


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = LeavePolicy
        fields = ["category", "annual_days", "requires_substitute", "max_days_per_request"]
        extra_kwargs = {"category": {"validators": []}}


class UnitSerializer(serializers.ModelSerializer):
    parent_name = serializers.CharField(source="parent.name", default="", read_only=True)

    class Meta:
        model = OrgUnit
        fields = ["id", "name", "head_user_id", "parent_name"]


class UnitWriteSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=80)
    head_user_id = serializers.IntegerField(allow_null=True)
    parent_name = serializers.CharField(max_length=80, required=False, allow_blank=True,
                                        default="")


class AuthorityRuleSerializer(serializers.ModelSerializer):
    unit_name = serializers.CharField(source="unit.name", default="", read_only=True)

    class Meta:
        model = AuthorityRule
        fields = ["id", "category", "unit_name", "applicant_kind", "sanctioning_user_id",
                  "establishment_user_id"]


class AuthorityRuleWriteSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=CATEGORIES)
    unit_name = serializers.CharField(required=False, allow_blank=True, default="")
    applicant_kind = serializers.ChoiceField(choices=["", "faculty", "staff"], default="")
    sanctioning_user_id = serializers.IntegerField()
    establishment_user_id = serializers.IntegerField(required=False, allow_null=True)


class SlaSerializer(serializers.ModelSerializer):
    state = serializers.ChoiceField(choices=sorted(s.value for s in PENDING))

    class Meta:
        model = SlaPolicy
        fields = ["state", "reminder_hours", "escalation_hours", "escalate_to_user_id"]


class DirectorSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()


class HolidaySerializer(serializers.Serializer):
    date = serializers.DateField()
    name = serializers.CharField(max_length=120)
    kind = serializers.ChoiceField(choices=["closed", "restricted"])


class CalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "title", "status", "published_at", "holidays"]


class CalendarWriteSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    title = serializers.CharField(max_length=120)
    holidays = HolidaySerializer(many=True)


class VacationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "name", "start_date", "end_date"]


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=[h.value for h in Half], default=Half.FULL.value)
    purpose = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                    default="")
    reference = serializers.CharField(max_length=255)


class CorrectionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=CATEGORIES)
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    days = serializers.DecimalField(max_digits=5, decimal_places=1)
    note = serializers.CharField(max_length=255)
