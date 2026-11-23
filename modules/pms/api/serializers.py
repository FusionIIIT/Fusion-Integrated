"""Wire format: outputs list every field read-only; inputs are explicit allow-lists."""
from __future__ import annotations

from rest_framework import serializers

from modules.pms.domain import appeals as ap
from modules.pms.domain import documents as d
from modules.pms.domain import licensing as lic
from modules.pms.domain import reports as rp
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation as v
from modules.pms.models import (
    Appeal,
    Application,
    Assessment,
    AttorneyAssignment,
    AuditEntry,
    Budget,
    Communication,
    Document,
    DocumentVersion,
    Escalation,
    Filing,
    Inventor,
    LegalAdvice,
    LegalRequest,
    LicenseAgreement,
    LicensingRequest,
    MaintenanceCycle,
    NegotiationNote,
    OfficeAction,
    PmsPolicy,
    PriorArtReference,
    ReportDefinition,
    ReportRun,
    ReviewCycle,
    RevisionResponse,
)


class Strict(serializers.Serializer):
    """An unknown key is refused rather than silently ignored."""

    def to_internal_value(self, data):
        if hasattr(data, "keys"):
            unknown = sorted(set(data.keys()) - set(self.fields))
            if unknown:
                raise serializers.ValidationError(
                    dict.fromkeys(unknown, "This field is not accepted here."))
        return super().to_internal_value(data)


def _name(serializer, user_id):
    if user_id is None:
        return ""
    people = serializer.context.get("names", {})
    return people.get(user_id, f"User {user_id}")


class _ChoiceAsText(serializers.CharField):
    """A model choice rendered as plain text, so PMS enums never collide with another module's."""

    def __init__(self, *, choices=None, **kwargs):
        kwargs.pop("allow_blank", None)
        super().__init__(allow_blank=True, **kwargs)


class _ReadOnly(serializers.ModelSerializer):
    serializer_choice_field = _ChoiceAsText

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        meta = getattr(cls, "Meta", None)
        if meta is not None and hasattr(meta, "fields"):
            meta.read_only_fields = meta.fields


# -- outputs -------------------------------------------------------------------
class PmsInventorSerializer(_ReadOnly):
    class Meta:
        model = Inventor
        fields = ("id", "user_id", "name", "email", "affiliation", "share_percent",
                  "agreement_completed_at", "agreement_reference", "consent_recorded_at")


class PmsReviewCycleSerializer(_ReadOnly):
    director_name = serializers.SerializerMethodField()

    class Meta:
        model = ReviewCycle
        fields = ("id", "cycle_no", "director_user_id", "director_name", "assigned_on",
                  "due_on", "status", "decision", "justification", "decided_at")

    def get_director_name(self, obj) -> str:
        return _name(self, obj.director_user_id)


class PmsAppealSerializer(_ReadOnly):
    director_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Appeal
        fields = ("id", "application_id", "director_user_id", "director_name", "grounds",
                  "justification", "status", "outcome", "modified_decision", "outcome_note",
                  "created_at", "decided_at")

    def get_director_name(self, obj) -> str:
        return _name(self, obj.director_user_id)


class PmsAssignmentSerializer(_ReadOnly):
    attorney_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(read_only=True)
    application_reference = serializers.CharField(source="application.reference",
                                                  read_only=True)
    application_title = serializers.CharField(source="application.title", read_only=True)

    class Meta:
        model = AttorneyAssignment
        fields = ("id", "application_id", "application_reference", "application_title",
                  "attorney_user_id", "attorney_name", "is_exception", "exception_reason",
                  "status", "responded_at", "decline_reason", "created_at")

    def get_attorney_name(self, obj) -> str:
        return _name(self, obj.attorney_user_id)


class PmsBudgetSerializer(_ReadOnly):
    application_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = Budget
        fields = ("id", "application_id", "filing_fee", "attorney_fee", "admin_cost", "total",
                  "status", "decision_note", "decided_at", "threshold_at_decision",
                  "availability", "routed_to", "external_reference", "external_decided_on",
                  "created_at")


class PmsFilingSerializer(_ReadOnly):
    class Meta:
        model = Filing
        fields = ("id", "jurisdiction", "office_name", "international_justification",
                  "external_filing_id", "filing_date", "confirmation_reference",
                  "format_validation", "created_at")


class PmsCommunicationSerializer(_ReadOnly):
    class Meta:
        model = Communication
        fields = ("id", "kind", "received_on", "reference", "details", "created_at")


class PmsOfficeActionSerializer(_ReadOnly):
    application_id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(source="communication.reference", read_only=True)
    received_on = serializers.DateField(source="communication.received_on", read_only=True)
    current_due_on = serializers.SerializerMethodField()
    extensions = serializers.SerializerMethodField()

    class Meta:
        model = OfficeAction
        fields = ("id", "application_id", "reference", "received_on", "response_due_on",
                  "current_due_on", "requires_applicant_review", "status", "draft_response",
                  "approved_at", "submitted_on", "submission_reference", "extensions")

    def get_current_due_on(self, obj) -> str | None:
        dates = [e.new_due_on for e in obj.extensions.all()]
        due = max(dates) if dates else obj.response_due_on
        return due.isoformat() if due else None

    def get_extensions(self, obj) -> list[dict]:
        return [{"new_due_on": e.new_due_on.isoformat(), "reason": e.reason}
                for e in obj.extensions.all()]


class PmsMaintenanceCycleSerializer(_ReadOnly):
    director_name = serializers.SerializerMethodField()
    application_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = MaintenanceCycle
        fields = ("id", "application_id", "seq", "due_on", "source", "status",
                  "deciding_director_user_id", "director_name", "decided_at", "decision_note",
                  "action_reference", "amount", "actioned_on")

    def get_director_name(self, obj) -> str:
        return _name(self, obj.deciding_director_user_id)


class PmsAssessmentSerializer(_ReadOnly):
    class Meta:
        model = Assessment
        fields = ("id", "analysis", "novelty", "non_obviousness", "utility", "recommendation",
                  "status", "finalized_at", "updated_at")


class PmsLegalRequestSerializer(_ReadOnly):
    class Meta:
        model = LegalRequest
        fields = ("id", "kind", "message", "created_at")


class PmsLegalAdviceSerializer(_ReadOnly):
    class Meta:
        model = LegalAdvice
        fields = ("id", "stage", "advice", "created_at")


class PmsRevisionResponseSerializer(_ReadOnly):
    class Meta:
        model = RevisionResponse
        fields = ("id", "version", "feedback_key", "response", "created_at")


LIST_FIELDS = ("id", "reference", "title", "status", "domain_code", "applicant_user_id",
               "applicant_name", "submitted_at", "updated_at", "revision_due_on",
               "appeal_due_on")


class PmsApplicationListSerializer(_ReadOnly):
    applicant_name = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = LIST_FIELDS

    def get_applicant_name(self, obj) -> str:
        return _name(self, obj.applicant_user_id)


class PmsApplicationDetailSerializer(PmsApplicationListSerializer):
    inventors = PmsInventorSerializer(many=True, read_only=True)
    review_cycles = PmsReviewCycleSerializer(many=True, read_only=True)
    appeals = PmsAppealSerializer(many=True, read_only=True)
    attorney_assignments = PmsAssignmentSerializer(many=True, read_only=True)
    budgets = PmsBudgetSerializer(many=True, read_only=True)
    filings = PmsFilingSerializer(many=True, read_only=True)
    communications = PmsCommunicationSerializer(many=True, read_only=True)
    office_actions = PmsOfficeActionSerializer(many=True, read_only=True)
    maintenance_cycles = PmsMaintenanceCycleSerializer(many=True, read_only=True)
    assessments = PmsAssessmentSerializer(many=True, read_only=True)
    legal_requests = PmsLegalRequestSerializer(many=True, read_only=True)
    legal_advice = PmsLegalAdviceSerializer(many=True, read_only=True)
    revision_responses = PmsRevisionResponseSerializer(many=True, read_only=True)
    relations = serializers.SerializerMethodField()
    feedback = serializers.SerializerMethodField()

    class Meta:
        model = Application
        fields = (*LIST_FIELDS, "abstract", "description", "claims",
                  "preferred_attorney_user_id", "version", "decided_on", "grant_date",
                  "grant_jurisdiction", "patent_number", "inventors", "review_cycles",
                  "appeals", "attorney_assignments", "budgets", "filings", "communications",
                  "office_actions", "maintenance_cycles", "assessments", "legal_requests",
                  "legal_advice", "revision_responses", "relations", "feedback")

    def get_relations(self, obj) -> list[str]:
        return sorted(self.context.get("relations", ()))

    def get_feedback(self, obj) -> dict:
        return self.context.get("feedback", {})


class PmsVersionSerializer(_ReadOnly):
    class Meta:
        model = DocumentVersion
        fields = ("id", "number", "original_name", "size_bytes", "sha256", "uploaded_at",
                  "uploaded_by_user_id", "is_current")


class PmsDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    kind = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    sensitivity = serializers.CharField(read_only=True)
    versions = PmsVersionSerializer(many=True, read_only=True)


class PmsDocumentRowSerializer(_ReadOnly):
    class Meta:
        model = Document
        fields = ("id", "kind", "title", "sensitivity", "updated_at")


class PmsRosterSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    domain_codes = serializers.ListField(child=serializers.CharField(), read_only=True)
    valid_from = serializers.DateTimeField(read_only=True)
    valid_to = serializers.DateTimeField(read_only=True)
    workload = serializers.SerializerMethodField()

    def get_name(self, obj) -> str:
        return _name(self, obj.user_id)

    def get_workload(self, obj) -> int:
        return self.context.get("workloads", {}).get(obj.user_id, 0)


class PmsCandidateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    domain_codes = serializers.SerializerMethodField()
    workload = serializers.IntegerField(read_only=True)

    def get_name(self, obj) -> str:
        return _name(self, obj.user_id)

    def get_domain_codes(self, obj) -> list[str]:
        return sorted(obj.domain_codes)


class PmsPanelOptionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(read_only=True)
    name = serializers.SerializerMethodField()
    domain_codes = serializers.ListField(child=serializers.CharField(), read_only=True)

    def get_name(self, obj) -> str:
        return _name(self, obj.user_id)


class PmsPriorArtSerializer(_ReadOnly):
    application_id = serializers.IntegerField(read_only=True)

    class Meta:
        model = PriorArtReference
        fields = ("id", "application_id", "kind", "title", "identifier", "url", "source_name",
                  "notes", "created_at")


class PmsNoteSerializer(_ReadOnly):
    class Meta:
        model = NegotiationNote
        fields = ("id", "author_user_id", "note", "created_at")


class PmsAgreementSerializer(_ReadOnly):
    class Meta:
        model = LicenseAgreement
        fields = ("id", "counterparty", "signed_on", "terms_summary", "financial_terms",
                  "financial_sync", "created_at")


class PmsLicensingSerializer(_ReadOnly):
    application_id = serializers.IntegerField(read_only=True)
    application_reference = serializers.CharField(source="application.reference",
                                                  read_only=True)
    notes = PmsNoteSerializer(many=True, read_only=True)
    agreement = serializers.SerializerMethodField()

    class Meta:
        model = LicensingRequest
        fields = ("id", "application_id", "application_reference", "kind", "summary", "status",
                  "route_kind", "routed_director_user_id", "committee_name", "routed_at",
                  "notes", "agreement", "created_at")

    def get_agreement(self, obj) -> dict | None:
        agreement = getattr(obj, "agreement", None)
        return PmsAgreementSerializer(agreement).data if agreement else None


class PmsEscalationSerializer(_ReadOnly):
    application_id = serializers.IntegerField(read_only=True)
    application_reference = serializers.CharField(source="application.reference",
                                                  read_only=True)

    class Meta:
        model = Escalation
        fields = ("id", "kind", "application_id", "application_reference", "subject_id",
                  "deadline", "status", "note", "handled_at", "created_at")


class PmsAuditSerializer(_ReadOnly):
    application_reference = serializers.SerializerMethodField()

    class Meta:
        model = AuditEntry
        fields = ("id", "at", "actor_user_id", "actor_role", "action", "application_id",
                  "application_reference", "object_type", "object_id", "from_state",
                  "to_state", "details")

    def get_application_reference(self, obj) -> str:
        return obj.application.reference if obj.application_id else ""


class PmsPolicySerializer(_ReadOnly):
    class Meta:
        model = PmsPolicy
        fields = ("version", "effective_from", "payload", "published_by_user_id")


class PmsReportDefinitionSerializer(_ReadOnly):
    runs = serializers.SerializerMethodField()

    class Meta:
        model = ReportDefinition
        fields = ("id", "name", "report_type", "filters", "columns", "schedule", "active",
                  "created_at", "runs")

    def get_runs(self, obj) -> list[dict]:
        return [{"id": r.id, "period": r.period, "created_at": r.created_at.isoformat()}
                for r in obj.runs.all().order_by("-id")[:12]]


class PmsReportRunSerializer(_ReadOnly):
    class Meta:
        model = ReportRun
        fields = ("id", "period", "created_at")


class PmsWorkItemSerializer(serializers.Serializer):
    kind = serializers.CharField(read_only=True)
    id = serializers.IntegerField(read_only=True)
    application_id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    title = serializers.CharField(read_only=True)
    status = serializers.CharField(read_only=True)


class PmsDeadlineSerializer(serializers.Serializer):
    kind = serializers.CharField(read_only=True)
    subject_id = serializers.IntegerField(read_only=True)
    application_id = serializers.IntegerField(read_only=True)
    reference = serializers.CharField(read_only=True)
    due_on = serializers.DateField(read_only=True)
    responsible = serializers.SerializerMethodField()
    missed = serializers.SerializerMethodField()

    def get_responsible(self, obj) -> str:
        return _name(self, obj.responsible_user_id)

    def get_missed(self, obj) -> bool:
        return obj.due_on < self.context["today"]


# -- inputs --------------------------------------------------------------------
class PmsApplicationIn(Strict):
    title = serializers.CharField(max_length=300, required=False, allow_blank=True)
    abstract = serializers.CharField(max_length=5000, required=False, allow_blank=True)
    description = serializers.CharField(max_length=100_000, required=False, allow_blank=True)
    claims = serializers.CharField(max_length=50_000, required=False, allow_blank=True)
    domain_code = serializers.CharField(max_length=40, required=False, allow_blank=True)
    preferred_attorney_user_id = serializers.IntegerField(required=False, allow_null=True,
                                                          min_value=1)


class PmsInventorIn(Strict):
    user_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    name = serializers.CharField(max_length=200, required=False, allow_blank=True)
    email = serializers.CharField(max_length=254, required=False, allow_blank=True)
    affiliation = serializers.CharField(max_length=200, required=False, allow_blank=True)
    share_percent = serializers.CharField(max_length=10)


class PmsInventorsIn(Strict):
    inventors = PmsInventorIn(many=True)


class PmsAgreementIn(Strict):
    agreement_reference = serializers.CharField(max_length=200, allow_blank=True)
    consent = serializers.BooleanField()


class PmsResubmitIn(Strict):
    responses = serializers.DictField(child=serializers.CharField(max_length=10_000,
                                                                  allow_blank=True))


class PmsWithdrawIn(Strict):
    reason = serializers.CharField(max_length=2000, allow_blank=True)
    consented_inventor_ids = serializers.ListField(child=serializers.IntegerField(min_value=1),
                                                   required=False, default=list, max_length=50)


class PmsAppealIn(Strict):
    grounds = serializers.CharField(max_length=5000, allow_blank=True)
    justification = serializers.CharField(max_length=10_000, allow_blank=True)


class PmsPersonIn(Strict):
    director_user_id = serializers.IntegerField(min_value=1)


class PmsDecisionIn(Strict):
    decision = serializers.ChoiceField(choices=("approve", "reject", "needs_revision"))
    justification = serializers.CharField(max_length=10_000, allow_blank=True)


class PmsAppealDecisionIn(Strict):
    outcome = serializers.ChoiceField(choices=ap.OUTCOMES)
    modified_decision = serializers.ChoiceField(choices=ap.MODIFIED_DECISIONS, required=False,
                                                allow_null=True)
    note = serializers.CharField(max_length=10_000, allow_blank=True)


class PmsRosterIn(Strict):
    user_id = serializers.IntegerField(min_value=1)
    domain_codes = serializers.ListField(child=serializers.CharField(max_length=40),
                                         max_length=50)


class PmsAttorneyIn(Strict):
    attorney_user_id = serializers.IntegerField(min_value=1)
    exception_reason = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                             default="")


class PmsRespondIn(Strict):
    accept = serializers.BooleanField()
    reason = serializers.CharField(max_length=2000, required=False, allow_blank=True,
                                   default="")


class PmsAssessmentIn(Strict):
    assessment_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    analysis = serializers.CharField(max_length=50_000, required=False, allow_blank=True)
    novelty = serializers.CharField(max_length=50_000, required=False, allow_blank=True)
    non_obviousness = serializers.CharField(max_length=50_000, required=False,
                                            allow_blank=True)
    utility = serializers.CharField(max_length=50_000, required=False, allow_blank=True)
    recommendation = serializers.ChoiceField(choices=("", *v.RECOMMENDATIONS), required=False)


class PmsLegalRequestIn(Strict):
    kind = serializers.ChoiceField(choices=("information", "extension"))
    message = serializers.CharField(max_length=5000, allow_blank=True)


class PmsAdviceIn(Strict):
    advice = serializers.CharField(max_length=20_000, allow_blank=True)


class PmsBudgetIn(Strict):
    filing_fee = serializers.CharField(max_length=20)
    attorney_fee = serializers.CharField(max_length=20)
    admin_cost = serializers.CharField(max_length=20)


class PmsBudgetDecisionIn(Strict):
    approve = serializers.BooleanField()
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class PmsRouteIn(Strict):
    routed_to = serializers.CharField(max_length=200, allow_blank=True)


class PmsExternalDecisionIn(Strict):
    approved = serializers.BooleanField()
    reference = serializers.CharField(max_length=200, allow_blank=True)
    decided_on = serializers.DateField()


class PmsFilingIn(Strict):
    jurisdiction = serializers.CharField(max_length=5)
    office_name = serializers.CharField(max_length=120, allow_blank=True)
    external_filing_id = serializers.CharField(max_length=64, allow_blank=True)
    filing_date = serializers.DateField()
    confirmation_reference = serializers.CharField(max_length=200, allow_blank=True)
    international_justification = serializers.CharField(max_length=5000, required=False,
                                                        allow_blank=True, default="")


class PmsCommunicationIn(Strict):
    kind = serializers.ChoiceField(choices=("office_action", "grant", "refusal", "other"))
    received_on = serializers.DateField()
    reference = serializers.CharField(max_length=200, allow_blank=True)
    details = serializers.CharField(max_length=20_000, required=False, allow_blank=True,
                                    default="")
    response_due_on = serializers.DateField(required=False, allow_null=True)
    requires_applicant_review = serializers.BooleanField(required=False, default=False)
    grant_date = serializers.DateField(required=False, allow_null=True)
    patent_number = serializers.CharField(max_length=64, required=False, allow_blank=True,
                                          default="")
    jurisdiction = serializers.CharField(max_length=5, required=False, allow_blank=True,
                                         default="")


class PmsDraftResponseIn(Strict):
    draft = serializers.CharField(max_length=100_000, allow_blank=True)


class PmsSubmissionIn(Strict):
    submitted_on = serializers.DateField()
    reference = serializers.CharField(max_length=200, allow_blank=True)


class PmsExtensionIn(Strict):
    new_due_on = serializers.DateField()
    reason = serializers.CharField(max_length=2000, allow_blank=True)


class PmsDueDateIn(Strict):
    due_on = serializers.DateField()


class PmsRenewalIn(Strict):
    renew = serializers.BooleanField()
    note = serializers.CharField(max_length=2000, required=False, allow_blank=True, default="")


class PmsMaintenanceActionIn(Strict):
    reference = serializers.CharField(max_length=200, allow_blank=True)
    amount = serializers.CharField(max_length=20)
    actioned_on = serializers.DateField()


class PmsUploadIn(Strict):
    file = serializers.FileField()
    kind = serializers.ChoiceField(choices=d.KINDS, required=False)
    title = serializers.CharField(max_length=200, required=False, allow_blank=True)
    sensitivity = serializers.ChoiceField(choices=d.SENSITIVITIES, required=False)
    document_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class PmsSensitivityIn(Strict):
    sensitivity = serializers.ChoiceField(choices=d.SENSITIVITIES)


class PmsSearchIn(Strict):
    query = serializers.CharField(max_length=500, allow_blank=True)
    application_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    classification_codes = serializers.ListField(child=serializers.CharField(max_length=20),
                                                 required=False, default=list, max_length=20)


class PmsReferenceIn(Strict):
    kind = serializers.ChoiceField(choices=("patent", "publication"))
    title = serializers.CharField(max_length=500, allow_blank=True)
    identifier = serializers.CharField(max_length=120, required=False, allow_blank=True,
                                       default="")
    url = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    source_name = serializers.CharField(max_length=120, required=False, allow_blank=True,
                                        default="")
    notes = serializers.CharField(max_length=10_000, required=False, allow_blank=True,
                                  default="")
    search_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)


class PmsLicensingIn(Strict):
    application_id = serializers.IntegerField(min_value=1)
    kind = serializers.ChoiceField(choices=lic.KINDS)
    summary = serializers.CharField(max_length=5000, allow_blank=True)


class PmsNoteIn(Strict):
    note = serializers.CharField(max_length=5000, allow_blank=True)


class PmsLicenseAgreementIn(Strict):
    counterparty = serializers.CharField(max_length=200, allow_blank=True)
    signed_on = serializers.DateField()
    terms_summary = serializers.CharField(max_length=20_000, allow_blank=True)
    financial_terms = serializers.CharField(max_length=20_000, required=False,
                                            allow_blank=True, default="")


class PmsHandleIn(Strict):
    action = serializers.ChoiceField(choices=("route", "resolve"))
    note = serializers.CharField(max_length=2000, allow_blank=True)


class PmsReportDefinitionIn(Strict):
    name = serializers.CharField(max_length=120, allow_blank=True)
    report_type = serializers.ChoiceField(choices=rp.TYPES)
    filters = serializers.DictField(child=serializers.CharField(max_length=40), required=False,
                                    default=dict)
    columns = serializers.ListField(child=serializers.CharField(max_length=40),
                                    required=False, default=list, max_length=20)
    schedule = serializers.ChoiceField(choices=rp.SCHEDULES)


class PmsPolicyIn(Strict):
    based_on_version = serializers.IntegerField(min_value=0)
    payload = serializers.DictField()


class PmsApplicationFilterIn(Strict):
    status = serializers.CharField(max_length=20, required=False)
    domain_code = serializers.CharField(max_length=40, required=False)
    q = serializers.CharField(max_length=100, required=False)

    def validate_status(self, value):
        if value not in sm.APPLICATION_STATUSES:
            raise serializers.ValidationError("Unknown status.")
        return value
    cursor = serializers.CharField(max_length=500, required=False)
    limit = serializers.IntegerField(min_value=1, max_value=100, required=False)

