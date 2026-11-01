"""Serializers for Patent Management System.

Explicit allow-lists for all fields. No fields = '__all__'.
"""

from __future__ import annotations

from rest_framework import serializers

from modules.pms.models import (
    ApplicationDocument,
    AttorneyAssignment,
    AttorneyPanel,
    DirectorAssignment,
    DirectorReview,
    ExtensionRequest,
    ExternalFilingRecord,
    Inventor,
    LicensingRequest,
    MaintenanceSchedule,
    OfficeAction,
    OfficeActionResponse,
    PatentabilityAssessment,
    PatentAppeal,
    PatentApplication,
    PatentAuditLog,
    PatentBudget,
    PatentLegalAdvice,
    PostGrantPatent,
    PriorArtAttachment,
    PriorArtSearchRecord,
)

# --- Sub-models ---


class InventorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Inventor
        fields = (
            "id",
            "user_id",
            "name",
            "email",
            "department",
            "is_lead",
            "share_percentage",
            "consent_status",
            "consent_date",
        )
        read_only_fields = ("id", "consent_date")


class InventorInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, default=0)
    name = serializers.CharField(max_length=200)
    email = serializers.EmailField()
    department = serializers.CharField(max_length=100)
    share_percentage = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    percentage_share = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False
    )
    is_lead = serializers.BooleanField(required=False, default=False)
    is_primary = serializers.BooleanField(required=False, default=False)


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = (
            "id",
            "document_type",
            "title",
            "version",
            "file_size",
            "mime_type",
            "sensitivity",
            "uploaded_by_user_id",
            "is_malware_scanned",
            "created_at",
        )
        read_only_fields = fields


class DirectorReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectorReview
        fields = (
            "id",
            "application_id",
            "director_user_id",
            "decision",
            "justification",
            "decided_at",
            "created_at",
        )
        read_only_fields = fields


class DirectorAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectorAssignment
        fields = (
            "id",
            "application_id",
            "director_user_id",
            "assigned_by_user_id",
            "due_at",
            "status",
            "created_at",
        )
        read_only_fields = fields


class PatentBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentBudget
        fields = (
            "id",
            "application_id",
            "filing_fees",
            "attorney_fees",
            "administrative_costs",
            "total_cost",
            "status",
            "director_user_id",
            "justification",
            "reviewed_at",
            "updated_at",
        )
        read_only_fields = fields


class AttorneyPanelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyPanel
        fields = (
            "id",
            "user_id",
            "name",
            "firm_name",
            "email",
            "specialization",
            "is_active",
            "max_workload",
            "current_workload",
            "created_at",
        )
        read_only_fields = ("id", "current_workload", "created_at")


class AttorneyAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyAssignment
        fields = (
            "id",
            "application_id",
            "attorney_user_id",
            "assigned_by_user_id",
            "status",
            "responded_at",
            "remarks",
            "created_at",
        )
        read_only_fields = fields


class PatentabilityAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentabilityAssessment
        fields = (
            "id",
            "application_id",
            "attorney_user_id",
            "recommendation",
            "novelty_analysis",
            "inventive_step_analysis",
            "utility_analysis",
            "prior_art_summary",
            "opinion_text",
            "assessed_at",
        )
        read_only_fields = fields


class PatentLegalAdviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentLegalAdvice
        fields = (
            "id",
            "application_id",
            "attorney_user_id",
            "topic",
            "advice_text",
            "created_at",
        )
        read_only_fields = fields


class ExternalFilingRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExternalFilingRecord
        fields = (
            "id",
            "application_id",
            "jurisdiction",
            "filing_number",
            "filing_date",
            "patent_office",
            "confirmation_details",
            "international_justification",
            "recorded_by_user_id",
            "created_at",
        )
        read_only_fields = fields


class OfficeActionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeActionResponse
        fields = (
            "id",
            "office_action_id",
            "attorney_user_id",
            "draft_text",
            "requires_applicant_approval",
            "applicant_approved",
            "applicant_approved_at",
            "submitted_at",
            "submission_details",
            "created_at",
        )
        read_only_fields = fields


class ExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtensionRequest
        fields = (
            "id",
            "office_action_id",
            "attorney_user_id",
            "requested_days",
            "reason",
            "filed_date",
            "is_granted",
            "new_deadline",
            "created_at",
        )
        read_only_fields = fields


class OfficeActionSerializer(serializers.ModelSerializer):
    responses = OfficeActionResponseSerializer(many=True, read_only=True)
    extension_requests = ExtensionRequestSerializer(many=True, read_only=True)

    class Meta:
        model = OfficeAction
        fields = (
            "id",
            "application_id",
            "action_number",
            "action_type",
            "issue_date",
            "response_deadline",
            "description",
            "status",
            "recorded_by_user_id",
            "created_at",
            "responses",
            "extension_requests",
        )
        read_only_fields = fields


class MaintenanceScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceSchedule
        fields = (
            "id",
            "post_grant_id",
            "cycle_year",
            "due_date",
            "fee_amount",
            "status",
            "payment_record_reference",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields


class PostGrantPatentSerializer(serializers.ModelSerializer):
    schedules = MaintenanceScheduleSerializer(many=True, read_only=True)

    class Meta:
        model = PostGrantPatent
        fields = (
            "id",
            "application_id",
            "patent_number",
            "grant_date",
            "term_years",
            "expiry_date",
            "current_cycle",
            "created_at",
            "schedules",
        )
        read_only_fields = fields


class LicensingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicensingRequest
        fields = (
            "id",
            "application_id",
            "licensee_name",
            "licensee_contact",
            "license_type",
            "proposed_terms",
            "royalty_rate",
            "financial_terms",
            "status",
            "requested_by_user_id",
            "reviewed_by_user_id",
            "review_notes",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PatentAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentAppeal
        fields = (
            "id",
            "application_id",
            "applicant_user_id",
            "grounds",
            "justification",
            "status",
            "filed_at",
            "resolved_at",
        )
        read_only_fields = fields


class PriorArtAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorArtAttachment
        fields = ("id", "search_record_id", "application_id", "relevance_notes", "attached_at")
        read_only_fields = fields


class PriorArtSearchRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorArtSearchRecord
        fields = (
            "id",
            "application_id",
            "user_id",
            "query_string",
            "databases_searched",
            "results_count",
            "session_notes",
            "created_at",
        )
        read_only_fields = fields


class PatentAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentAuditLog
        fields = (
            "id",
            "application_id",
            "user_id",
            "actor_role",
            "action_type",
            "previous_state",
            "new_state",
            "details",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields


# --- Patent Application Serializers ---


class PatentApplicationListSerializer(serializers.ModelSerializer):
    primary_inventor_name = serializers.SerializerMethodField()
    has_budget = serializers.SerializerMethodField()
    budget_status = serializers.SerializerMethodField()

    class Meta:
        model = PatentApplication
        fields = (
            "id",
            "application_no",
            "title",
            "domain",
            "status",
            "user_id",
            "primary_inventor_name",
            "has_budget",
            "budget_status",
            "submitted_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_primary_inventor_name(self, obj: PatentApplication) -> str:
        inv = obj.inventors.filter(is_lead=True).first()
        return inv.name if inv else ""

    def get_has_budget(self, obj: PatentApplication) -> bool:
        return hasattr(obj, "budget") and obj.budget is not None

    def get_budget_status(self, obj: PatentApplication) -> str:
        return obj.budget.status if hasattr(obj, "budget") and obj.budget else "none"


class PatentApplicationDetailSerializer(serializers.ModelSerializer):
    inventors = InventorSerializer(many=True, read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    reviews = DirectorReviewSerializer(many=True, read_only=True)
    budget = PatentBudgetSerializer(read_only=True)
    filing_record = ExternalFilingRecordSerializer(read_only=True)
    office_actions = OfficeActionSerializer(many=True, read_only=True)
    post_grant = PostGrantPatentSerializer(read_only=True)
    appeals = PatentAppealSerializer(many=True, read_only=True)

    class Meta:
        model = PatentApplication
        fields = (
            "id",
            "application_no",
            "title",
            "abstract",
            "description",
            "claims",
            "domain",
            "filing_type",
            "status",
            "user_id",
            "is_confidential",
            "submitted_at",
            "revision_deadline",
            "created_at",
            "updated_at",
            "inventors",
            "documents",
            "reviews",
            "budget",
            "filing_record",
            "office_actions",
            "post_grant",
            "appeals",
        )
        read_only_fields = fields


# --- Action / Input Serializers ---


class SubmitApplicationInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    abstract = serializers.CharField()
    description = serializers.CharField()
    claims = serializers.CharField()
    domain = serializers.CharField(max_length=100)
    keywords = serializers.CharField(required=False, allow_blank=True, default="")
    inventors = InventorInputSerializer(many=True, required=False, default=list)


class ReviseApplicationInputSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, required=False)
    abstract = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    claims = serializers.CharField(required=False)
    domain = serializers.CharField(max_length=100, required=False)
    keywords = serializers.CharField(required=False, allow_blank=True)
    revision_notes = serializers.CharField(required=False, allow_blank=True, default="")


class WithdrawApplicationInputSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class AssignDirectorInputSerializer(serializers.Serializer):
    director_user_id = serializers.IntegerField()


class DirectorReviewInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject", "needs_revision"])
    justification = serializers.CharField(min_length=50)


class AssignAttorneyInputSerializer(serializers.Serializer):
    attorney_user_id = serializers.IntegerField()


class AttorneyRespondInputSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class PatentabilityAssessmentInputSerializer(serializers.Serializer):
    recommendation = serializers.ChoiceField(
        choices=["file_patent", "do_not_file", "needs_more_prior_art", "needs_amendment"]
    )
    novelty_analysis = serializers.CharField(min_length=5)
    inventive_step_analysis = serializers.CharField(min_length=5)
    utility_analysis = serializers.CharField(min_length=5, required=False)
    industrial_applicability = serializers.CharField(min_length=5, required=False)
    prior_art_summary = serializers.CharField(min_length=5, required=False)
    prior_art_findings = serializers.CharField(min_length=5, required=False)
    opinion_text = serializers.CharField(min_length=5, required=False)
    detailed_opinion = serializers.CharField(min_length=5, required=False)


class PatentLegalAdviceInputSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=200, required=False)
    advice_type = serializers.CharField(max_length=100, required=False)
    summary = serializers.CharField(max_length=500, required=False)
    advice_text = serializers.CharField()


class BudgetCreateInputSerializer(serializers.Serializer):
    filing_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    attorney_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    administrative_costs = serializers.DecimalField(max_digits=12, decimal_places=2)


class BudgetDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    justification = serializers.CharField(required=False, allow_blank=True, default="")


class ExternalFilingInputSerializer(serializers.Serializer):
    jurisdiction = serializers.CharField(max_length=10)
    filing_number = serializers.CharField(max_length=100)
    filing_date = serializers.DateField()
    patent_office = serializers.CharField(max_length=200)
    confirmation_details = serializers.CharField(min_length=5)
    international_justification = serializers.CharField(
        required=False, allow_blank=True, default=""
    )


class OfficeActionCreateInputSerializer(serializers.Serializer):
    action_number = serializers.CharField(max_length=100)
    issue_date = serializers.DateField()
    response_deadline = serializers.DateField()
    action_type = serializers.CharField(max_length=100)
    description = serializers.CharField()


class OfficeActionResponseInputSerializer(serializers.Serializer):
    draft_text = serializers.CharField(required=False)
    response_text = serializers.CharField(required=False)
    requires_applicant_approval = serializers.BooleanField(required=False, default=True)
    requires_applicant_review = serializers.BooleanField(required=False, default=True)


class OfficeActionSubmitInputSerializer(serializers.Serializer):
    submission_details = serializers.CharField(required=False, allow_blank=True, default="")


class ExtensionRequestInputSerializer(serializers.Serializer):
    requested_days = serializers.IntegerField(min_value=1, max_value=90)
    reason = serializers.CharField()


class PostGrantInitInputSerializer(serializers.Serializer):
    grant_number = serializers.CharField(max_length=100)
    grant_date = serializers.DateField()
    patent_document_url = serializers.CharField(required=False, allow_blank=True, default="")


class MaintenanceDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["renew", "do_not_renew"])
    justification = serializers.CharField(min_length=5)


class MaintenancePaymentInputSerializer(serializers.Serializer):
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    payment_reference = serializers.CharField(max_length=200)


class LicensingRequestInputSerializer(serializers.Serializer):
    licensee_name = serializers.CharField(max_length=200)
    licensee_contact = serializers.CharField(max_length=200)
    license_type = serializers.CharField(max_length=100)
    proposed_terms = serializers.CharField()
    royalty_rate = serializers.DecimalField(
        max_digits=5, decimal_places=2, required=False, allow_null=True
    )
    financial_terms = serializers.CharField(required=False, allow_blank=True, default="")


class LicensingReviewInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    review_notes = serializers.CharField(min_length=5)


class AppealCreateInputSerializer(serializers.Serializer):
    grounds = serializers.CharField(min_length=10)
    justification = serializers.CharField(min_length=10)


class AppealReviewInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["remand", "uphold", "modify"])
    justification = serializers.CharField(min_length=10)


class PriorArtSearchInputSerializer(serializers.Serializer):
    keywords = serializers.CharField(required=False)
    query_string = serializers.CharField(required=False)
    databases_searched = serializers.CharField()
    results_summary = serializers.CharField(required=False, allow_blank=True)
    session_notes = serializers.CharField(required=False, allow_blank=True)
    results_count = serializers.IntegerField(required=False, default=0)


class PriorArtAttachInputSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    relevance_notes = serializers.CharField(required=False, allow_blank=True, default="")
