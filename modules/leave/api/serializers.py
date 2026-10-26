"""Shapes on the wire; requests are read-only because none is edited in place (BR-EL-034)."""
from rest_framework import serializers

from modules.leave.domain import categories as cat
from modules.leave.models import (
    Holiday,
    HolidayCalendar,
    LeaveRequest,
    LedgerEntry,
    RequestEvent,
    Resumption,
    Substitution,
    Task,
    VacationPeriod,
    YearEndRun,
)


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = RequestEvent
        fields = ["id", "event", "from_status", "to_status", "actor_user_id", "actor_role",
                  "outcome", "remarks", "at"]


class ResumptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Resumption
        fields = ["id", "resumption_date", "details", "status", "outcome", "actual_end_date",
                  "adjustment_days", "reviewed_at", "review_remarks"]


class SubstitutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Substitution
        fields = ["id", "substitute_user_id", "status", "responded_at", "remarks"]


class LeaveRequestSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    category_label = serializers.SerializerMethodField()
    parent_id = serializers.IntegerField(read_only=True, allow_null=True)

    class Meta:
        model = LeaveRequest
        fields = ["id", "kind", "parent_id", "user_id", "category", "category_label",
                  "start_date", "end_date", "half", "days", "leave_year", "status",
                  "status_label", "purpose", "station_leave", "station_from", "station_to",
                  "station_address", "evidence_reference", "applicant_kind",
                  "applicant_department", "is_director_applicant", "unit_head_outcome",
                  "decision", "decided_role", "decided_at", "decision_remarks", "source",
                  "offline_reference", "submitted_at", "withdrawn_at", "created_at"]
        read_only_fields = fields

    def get_category_label(self, obj) -> str:
        return cat.LABELS.get(obj.category, obj.category)


class LeaveRequestDetailSerializer(LeaveRequestSerializer):
    events = EventSerializer(many=True, read_only=True)
    substitutions = SubstitutionSerializer(many=True, read_only=True)
    resumption = serializers.SerializerMethodField()
    effective_end = serializers.SerializerMethodField()

    class Meta(LeaveRequestSerializer.Meta):
        fields = [*LeaveRequestSerializer.Meta.fields, "events", "substitutions", "resumption",
                  "effective_end"]
        read_only_fields = fields

    def get_resumption(self, obj) -> dict | None:
        res = Resumption.objects.filter(leave=obj).first()
        return ResumptionSerializer(res).data if res else None

    def get_effective_end(self, obj) -> str:
        from modules.leave.services.workflow import effective_end

        return str(effective_end(obj)) if obj.kind == "new" else str(obj.end_date)


class LeaveApplySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=list(cat.ALL))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=LeaveRequest.HALF, required=False, default="")
    purpose = serializers.CharField(max_length=2000, allow_blank=True, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_from = serializers.DateField(required=False, allow_null=True, default=None)
    station_to = serializers.DateField(required=False, allow_null=True, default=None)
    station_address = serializers.CharField(max_length=300, allow_blank=True, default="")
    evidence_reference = serializers.CharField(max_length=500, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class ExtensionSerializer(serializers.Serializer):
    end_date = serializers.DateField()
    purpose = serializers.CharField(max_length=2000, allow_blank=True, default="")
    station_leave = serializers.BooleanField(required=False, default=False)
    station_from = serializers.DateField(required=False, allow_null=True, default=None)
    station_to = serializers.DateField(required=False, allow_null=True, default=None)
    station_address = serializers.CharField(max_length=300, allow_blank=True, default="")
    evidence_reference = serializers.CharField(max_length=500, allow_blank=True, default="")
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class ReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, allow_blank=True, default="")


class NomineeSerializer(serializers.Serializer):
    substitute_user_id = serializers.IntegerField()


class ResumeSerializer(serializers.Serializer):
    resumption_date = serializers.DateField()
    details = serializers.CharField(max_length=500, allow_blank=True, default="")


class RespondSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(max_length=300, allow_blank=True, default="")


class DecideSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["approve", "reject", "recommend", "not_recommend",
                                              "forward", "review"])
    remarks = serializers.CharField(max_length=500, allow_blank=True, default="")


class BalanceSerializer(serializers.Serializer):
    category = serializers.CharField()
    label = serializers.CharField()
    balance = serializers.DecimalField(max_digits=7, decimal_places=2)
    pending = serializers.DecimalField(max_digits=7, decimal_places=2)
    available = serializers.DecimalField(max_digits=7, decimal_places=2)
    applicable = serializers.BooleanField()


class CategoryOptionSerializer(serializers.Serializer):
    category = serializers.CharField()
    label = serializers.CharField()
    substitute = serializers.CharField()
    evidence_min_days = serializers.DecimalField(max_digits=5, decimal_places=1, allow_null=True)
    half_day = serializers.BooleanField()
    extendable = serializers.BooleanField()


class OverviewSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    kind = serializers.CharField()
    department = serializers.CharField()
    balances = BalanceSerializer(many=True)
    categories = CategoryOptionSerializer(many=True)
    configured = serializers.BooleanField()


class LedgerSerializer(serializers.ModelSerializer):
    entry_label = serializers.CharField(source="get_entry_type_display", read_only=True)

    class Meta:
        model = LedgerEntry
        fields = ["id", "leave_year", "category", "delta", "entry_type", "entry_label",
                  "request_id", "note", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)
    applicant_name = serializers.SerializerMethodField()
    actions = serializers.SerializerMethodField()
    resumption = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = ["id", "step", "assignee_designation", "opened_at", "reminded_at",
                  "escalated_at", "request", "applicant_name", "actions", "resumption"]

    def get_applicant_name(self, obj) -> str:
        people = self.context.get("people", {})
        p = people.get(obj.request.user_id)
        return p.display_name if p else f"User {obj.request.user_id}"

    def get_actions(self, obj) -> list[str]:
        from modules.leave.services.queue import actions_for

        return actions_for(obj)

    def get_resumption(self, obj) -> dict | None:
        if obj.step != "resumption_review":
            return None
        res = getattr(obj.request, "resumption", None)
        return ResumptionSerializer(res).data if res else None


class SubstitutionRequestSerializer(serializers.ModelSerializer):
    request = LeaveRequestSerializer(read_only=True)
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = Substitution
        fields = ["id", "status", "created_at", "request", "applicant_name"]

    def get_applicant_name(self, obj) -> str:
        p = self.context.get("people", {}).get(obj.request.user_id)
        return p.display_name if p else f"User {obj.request.user_id}"


class PersonSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    display_name = serializers.CharField()
    username = serializers.CharField()
    kind = serializers.CharField()
    department = serializers.CharField()


class HolidaySerializer(serializers.ModelSerializer):
    class Meta:
        model = Holiday
        fields = ["date", "name", "kind"]


class CalendarSerializer(serializers.ModelSerializer):
    holidays = HolidaySerializer(many=True, read_only=True)

    class Meta:
        model = HolidayCalendar
        fields = ["id", "year", "version", "status", "published_at", "holidays"]


class CalendarCreateSerializer(serializers.Serializer):
    year = serializers.IntegerField(min_value=2000, max_value=2100)


class CalendarEntriesSerializer(serializers.Serializer):
    holidays = HolidaySerializer(many=True)


class VacationSerializer(serializers.ModelSerializer):
    class Meta:
        model = VacationPeriod
        fields = ["id", "label", "start_date", "end_date", "source_reference"]


class EffectiveCalendarSerializer(serializers.Serializer):
    year = serializers.IntegerField()
    published = serializers.BooleanField()
    holidays = HolidaySerializer(many=True)
    vacations = VacationSerializer(many=True)


class CategoryRuleSerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=list(cat.ALL))
    annual_entitlement = serializers.DecimalField(max_digits=5, decimal_places=1)
    substitute = serializers.ChoiceField(choices=["required", "optional", "none"])
    evidence_min_days = serializers.DecimalField(max_digits=5, decimal_places=1, allow_null=True,
                                                 required=False, default=None)


class PolicySerializer(serializers.Serializer):
    revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    rules = CategoryRuleSerializer(many=True)
    weekend_days = serializers.ListField(child=serializers.IntegerField(min_value=0, max_value=6))
    max_backdate_days = serializers.IntegerField(min_value=0)
    note = serializers.CharField(max_length=300, allow_blank=True, default="", write_only=True)


class OrgUnitSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=100)
    unit_head_designation = serializers.CharField(max_length=155)
    head_leave_designation = serializers.CharField(max_length=155, allow_blank=True, default="")


class RouteSerializer(serializers.Serializer):
    employee_kind = serializers.ChoiceField(choices=["", "faculty", "staff"], default="")
    category = serializers.CharField(max_length=4, allow_blank=True, default="")
    department = serializers.CharField(max_length=100, allow_blank=True, default="")
    applicant_designation = serializers.CharField(max_length=155, allow_blank=True, default="")
    establishment_designation = serializers.CharField(max_length=155, allow_blank=True,
                                                      default="")
    sanction_designation = serializers.CharField(max_length=155)


class HierarchySerializer(serializers.Serializer):
    revision_id = serializers.IntegerField(read_only=True, allow_null=True)
    units = OrgUnitSerializer(many=True)
    routes = RouteSerializer(many=True)
    note = serializers.CharField(max_length=300, allow_blank=True, default="", write_only=True)
    choices = serializers.DictField(child=serializers.ListField(child=serializers.CharField()),
                                    read_only=True)
    warnings = serializers.ListField(child=serializers.CharField(), read_only=True)


class SlaRuleSerializer(serializers.Serializer):
    step = serializers.CharField(max_length=24)
    reminder_hours = serializers.IntegerField(min_value=1)
    escalation_hours = serializers.IntegerField(min_value=1)
    action = serializers.ChoiceField(choices=["notify", "reassign"], default="notify")
    escalate_to = serializers.CharField(max_length=155, allow_blank=True, default="")


class SlaSerializer(serializers.Serializer):
    rules = SlaRuleSerializer(many=True)
    note = serializers.CharField(max_length=300, allow_blank=True, default="", write_only=True)


class OfflineRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    category = serializers.ChoiceField(choices=list(cat.ALL))
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half = serializers.ChoiceField(choices=LeaveRequest.HALF, required=False, default="")
    purpose = serializers.CharField(max_length=2000, allow_blank=True, default="")
    sanction_reference = serializers.CharField(max_length=200)
    reason = serializers.ChoiceField(choices=["illness", "connectivity", "server_unavailable",
                                              "other"])
    reason_detail = serializers.CharField(max_length=250, allow_blank=True, default="")


class AdjustmentSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField(min_value=2000, max_value=2100)
    category = serializers.ChoiceField(choices=list(cat.ALL))
    delta = serializers.DecimalField(max_digits=6, decimal_places=1)
    reference = serializers.CharField(max_length=80)
    note = serializers.CharField(max_length=300)


class RecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    year = serializers.IntegerField()
    person = PersonSerializer(allow_null=True)
    balances = BalanceSerializer(many=True)
    requests = LeaveRequestSerializer(many=True)
    ledger = LedgerSerializer(many=True)


class YearEndRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = YearEndRun
        fields = ["year", "status", "accounts_processed", "entries_written", "exceptions",
                  "finished_at"]


class ReadinessSerializer(serializers.Serializer):
    ready = serializers.BooleanField()
    unmet = serializers.ListField(child=serializers.CharField())
    warnings = serializers.ListField(child=serializers.CharField())
