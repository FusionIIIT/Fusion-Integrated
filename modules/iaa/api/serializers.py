"""Request and response shapes; validation of input shape only, never policy."""
from __future__ import annotations

from rest_framework import serializers

from modules.iaa.domain.policy import ANOMALY_CATEGORIES
from modules.iaa.models import (
    Anomaly,
    ApprovalStep,
    AuditObservation,
    BudgetEntry,
    ClarificationQuery,
    FinancialRecord,
    FinancialYear,
    Notification,
    ObservationResponse,
    PolicyVersion,
    SupportingDocument,
    TrailEntry,
)

HTTPS = serializers.RegexField(r"^https://", max_length=500,
                               error_messages={"invalid": "Use an https:// link."})


class DocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportingDocument
        fields = ["id", "title", "link", "added_by", "created_at"]


class QuerySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClarificationQuery
        fields = ["id", "question", "raised_role", "response", "responded_at", "created_at"]


class StepSerializer(serializers.ModelSerializer):
    status = serializers.CharField(read_only=True)

    class Meta:
        model = ApprovalStep
        fields = ["id", "level", "designation", "status", "assigned_at", "via_escalation",
                  "decided_role", "decided_at", "remarks"]


class RecordSerializer(serializers.ModelSerializer):
    financial_year = serializers.SlugRelatedField(slug_field="code", read_only=True)
    kind = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = FinancialRecord
        fields = ["id", "kind", "status", "user_id", "department", "request_type", "title",
                  "description", "amount", "purpose", "trip_start", "trip_end",
                  "financial_year", "submitted_at", "route_levels", "current_level",
                  "processing_reference", "processing_note", "processed_at",
                  "created_at", "updated_at"]


class RecordDetailSerializer(RecordSerializer):
    documents = DocumentSerializer(many=True, read_only=True)
    queries = QuerySerializer(many=True, read_only=True)
    steps = StepSerializer(many=True, read_only=True)

    class Meta(RecordSerializer.Meta):
        fields = [*RecordSerializer.Meta.fields, "documents", "queries", "steps"]


class DocumentInSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    link = HTTPS


class ExpenseDraftSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=128, required=False, allow_blank=True)
    request_type = serializers.CharField(max_length=64, required=False, allow_blank=True)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    description = serializers.CharField(required=False, allow_blank=True)
    amount = serializers.DecimalField(max_digits=14, decimal_places=2, required=False,
                                      allow_null=True, min_value=0)


class CreateRecordSerializer(ExpenseDraftSerializer):
    kind = serializers.RegexField(r"^(expense|ta)$",
                                  error_messages={"invalid": "Use 'expense' or 'ta'."})
    purpose = serializers.CharField(required=False, allow_blank=True)
    trip_start = serializers.DateField(required=False, allow_null=True)
    trip_end = serializers.DateField(required=False, allow_null=True)
    documents = DocumentInSerializer(many=True, required=False)


class TextSerializer(serializers.Serializer):
    text = serializers.CharField(allow_blank=True)


class ValidateSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["verify", "reject"], default="verify")
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(allow_blank=True)


class ProcessingSerializer(serializers.Serializer):
    reference = serializers.CharField(max_length=128, allow_blank=True)
    note = serializers.CharField(required=False, allow_blank=True, default="")


class TrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = TrailEntry
        fields = ["id", "action", "from_status", "to_status", "actor_user_id", "actor_role",
                  "remarks", "created_at"]


class AnomalySerializer(serializers.ModelSerializer):
    category = serializers.CharField(read_only=True)
    source = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = Anomaly
        fields = ["id", "record", "category", "source", "description", "status",
                  "resolver_chain", "resolver_level", "assigned_role", "raised_role",
                  "resolved_role", "resolved_at", "resolution", "created_at"]


class FlagAnomalySerializer(serializers.Serializer):
    category = serializers.ChoiceField(choices=ANOMALY_CATEGORIES)
    description = serializers.CharField()
    record_id = serializers.IntegerField(required=False, allow_null=True)


class ResponseSerializer(serializers.ModelSerializer):
    verdict = serializers.CharField(read_only=True)

    class Meta:
        model = ObservationResponse
        fields = ["id", "cycle", "corrective_action", "evidence_link", "verdict",
                  "review_remarks", "reviewed_at", "created_at"]


class ObservationSerializer(serializers.ModelSerializer):
    responses = ResponseSerializer(many=True, read_only=True)
    status = serializers.CharField(read_only=True)

    class Meta:
        model = AuditObservation
        fields = ["id", "record", "respondent_user_id", "title", "detail", "status", "cycle",
                  "raised_role", "created_at", "responses"]


class RaiseObservationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=200)
    detail = serializers.CharField()
    record_id = serializers.IntegerField(required=False, allow_null=True)
    respondent_user_id = serializers.IntegerField(required=False, allow_null=True)


class RespondObservationSerializer(serializers.Serializer):
    corrective_action = serializers.CharField(allow_blank=True)
    evidence_link = serializers.RegexField(r"^https://", max_length=500, required=False,
                                           allow_blank=True, default="")


class ReviewObservationSerializer(serializers.Serializer):
    verdict = serializers.ChoiceField(choices=["satisfactory", "unsatisfactory"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class NotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Notification
        fields = ["id", "kind", "message", "entity", "entity_id", "created_at"]


class PolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = PolicyVersion
        fields = ["id", "effective_from", "approval_timeout_hours", "ta_high_value_threshold",
                  "budget_check_required", "request_types", "required_documents", "routes",
                  "anomaly_resolvers", "created_role", "created_at"]


class PublishPolicySerializer(serializers.Serializer):
    effective_from = serializers.DateTimeField(required=False, allow_null=True)
    approval_timeout_hours = serializers.IntegerField()
    ta_high_value_threshold = serializers.DecimalField(max_digits=14, decimal_places=2)
    budget_check_required = serializers.BooleanField(default=True)
    request_types = serializers.ListField(child=serializers.CharField(max_length=64))
    required_documents = serializers.DictField(child=serializers.IntegerField(min_value=0))
    routes = serializers.ListField(child=serializers.DictField())
    anomaly_resolvers = serializers.DictField(child=serializers.ListField(
        child=serializers.CharField(max_length=64)))


class FinancialYearSerializer(serializers.ModelSerializer):
    class Meta:
        model = FinancialYear
        fields = ["id", "code", "starts_on", "ends_on"]


class BudgetEntrySerializer(serializers.ModelSerializer):
    financial_year = serializers.SlugRelatedField(slug_field="code", read_only=True)
    kind = serializers.CharField(read_only=True)

    class Meta:
        model = BudgetEntry
        fields = ["id", "financial_year", "department", "kind", "amount", "record", "note",
                  "created_at"]


class BudgetEntryInSerializer(serializers.Serializer):
    financial_year_id = serializers.IntegerField()
    department = serializers.CharField(max_length=128)
    kind = serializers.RegexField(r"^(allocation|adjustment)$",
                                  error_messages={"invalid": "Use 'allocation' or 'adjustment'."})
    amount = serializers.DecimalField(max_digits=14, decimal_places=2)
    note = serializers.CharField(required=False, allow_blank=True, default="", max_length=255)
