"""PMS API Serializers."""

from __future__ import annotations

from rest_framework import serializers

from modules.pms.models import (
    ApplicationDocument,
    AttorneyAssignment,
    AttorneyPanel,
    CoInventor,
    DirectorReview,
    LicensingRequest,
    OfficeAction,
    PatentabilityAssessment,
    PatentAppeal,
    PatentApplication,
    PatentBudget,
    PatentLegalAdvice,
    PmsAuditTrail,
    PostGrantMaintenance,
    PriorArtReference,
)


class CoInventorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoInventor
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "department",
            "ownership_percentage",
            "consent_given",
            "agreement_signed",
            "electronic_signature",
            "signed_at",
            "withdrawal_consent_given",
        ]


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "doc_type",
            "title",
            "file_format",
            "file_size_bytes",
            "sensitivity",
            "version",
            "is_current",
            "uploaded_by_user_id",
            "file_url",
            "created_at",
        ]


class DirectorReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectorReview
        fields = [
            "id",
            "director_user_id",
            "decision",
            "justification",
            "feedback",
            "decided_at",
        ]


class PatentBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentBudget
        fields = [
            "id",
            "filing_fees",
            "attorney_fees",
            "administrative_costs",
            "total_cost",
            "status",
            "threshold_limit",
            "decided_by_user_id",
            "decided_at",
            "justification",
        ]


class AttorneyAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyAssignment
        fields = [
            "id",
            "attorney_user_id",
            "assigned_by_user_id",
            "status",
            "decline_reason",
            "decided_at",
            "is_active",
            "created_at",
        ]


class AttorneyPanelSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyPanel
        fields = [
            "id",
            "attorney_user_id",
            "name",
            "firm_name",
            "email",
            "is_approved",
            "expertise_domains",
            "current_workload",
            "max_workload",
        ]


class PatentabilityAssessmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentabilityAssessment
        fields = [
            "id",
            "attorney_user_id",
            "novelty_score",
            "non_obviousness_score",
            "utility_score",
            "recommendation",
            "opinion_text",
            "created_at",
        ]


class PriorArtReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorArtReference
        fields = [
            "id",
            "source",
            "reference_id",
            "title",
            "authors",
            "relevance",
            "notes",
            "attached_by_user_id",
            "created_at",
        ]


class OfficeActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeAction
        fields = [
            "id",
            "action_type",
            "issue_date",
            "due_date",
            "details",
            "status",
            "requires_applicant_review",
            "draft_response",
            "applicant_approved",
            "extension_months",
            "response_submitted_date",
            "submission_details",
            "created_at",
        ]


class PostGrantMaintenanceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PostGrantMaintenance
        fields = [
            "id",
            "cycle_number",
            "fee_due_date",
            "fee_amount",
            "decision_requested",
            "director_decision",
            "renewal_decided_at",
            "maintenance_status",
            "action_recorded_date",
            "transaction_reference",
        ]


class LicensingRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = LicensingRequest
        fields = [
            "id",
            "requested_by_user_id",
            "licensee_name",
            "request_type",
            "commercial_terms",
            "status",
            "negotiation_notes",
            "agreement_reference",
            "is_confidential",
            "created_at",
        ]


class PatentAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentAppeal
        fields = [
            "id",
            "applicant_user_id",
            "grounds",
            "justification",
            "status",
            "outcome",
            "director_user_id",
            "outcome_justification",
            "decided_at",
            "created_at",
        ]


class PatentLegalAdviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentLegalAdvice
        fields = [
            "id",
            "attorney_user_id",
            "stage",
            "advice_text",
            "created_at",
        ]


class PmsAuditTrailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PmsAuditTrail
        fields = [
            "id",
            "application_id",
            "actor_user_id",
            "action_type",
            "from_state",
            "to_state",
            "details",
            "timestamp",
        ]


class PatentApplicationReadSerializer(serializers.ModelSerializer):
    coinventors = CoInventorSerializer(many=True, read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    budget = PatentBudgetSerializer(read_only=True)
    director_reviews = DirectorReviewSerializer(many=True, read_only=True)
    attorney_assignments = AttorneyAssignmentSerializer(many=True, read_only=True)
    office_actions = OfficeActionSerializer(many=True, read_only=True)
    maintenance_records = PostGrantMaintenanceSerializer(many=True, read_only=True)

    class Meta:
        model = PatentApplication
        fields = [
            "id",
            "application_no",
            "title",
            "abstract",
            "detailed_description",
            "claims",
            "domain",
            "status",
            "applicant_user_id",
            "assigned_director_user_id",
            "assigned_attorney_user_id",
            "director_assigned_at",
            "review_deadline",
            "revision_deadline",
            "jurisdiction",
            "is_international",
            "international_justification",
            "external_filing_id",
            "external_filing_date",
            "filing_confirmation",
            "format_validated",
            "grant_date",
            "patent_number",
            "is_withdrawn",
            "withdrawal_reason",
            "withdrawal_date",
            "created_at",
            "updated_at",
            "coinventors",
            "documents",
            "budget",
            "director_reviews",
            "attorney_assignments",
            "office_actions",
            "maintenance_records",
        ]


class SubmitApplicationWriteSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=255)
    abstract = serializers.CharField()
    detailed_description = serializers.CharField()
    claims = serializers.CharField()
    domain = serializers.CharField(max_length=100)
    jurisdiction = serializers.CharField(max_length=50, default="IN")
    is_international = serializers.BooleanField(default=False)
    international_justification = serializers.CharField(required=False, allow_blank=True)
    preferred_attorney_id = serializers.IntegerField(required=False, allow_null=True)
    coinventors = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    documents = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class ReviseApplicationSerializer(serializers.Serializer):
    feedback_response = serializers.CharField()
    title = serializers.CharField(required=False, allow_blank=True)
    abstract = serializers.CharField(required=False, allow_blank=True)
    detailed_description = serializers.CharField(required=False, allow_blank=True)
    claims = serializers.CharField(required=False, allow_blank=True)
    documents = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class WithdrawApplicationSerializer(serializers.Serializer):
    reason = serializers.CharField()


class AssignDirectorSerializer(serializers.Serializer):
    director_user_id = serializers.IntegerField()


class SubmitReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["Approve", "Reject", "Needs Revision"])
    justification = serializers.CharField(min_length=50)
    feedback = serializers.CharField(required=False, allow_blank=True)


class FileAppealSerializer(serializers.Serializer):
    grounds = serializers.CharField()
    justification = serializers.CharField()


class ReviewAppealSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(
        choices=["Uphold Rejection", "Remand for Amendment", "Modify Decision"]
    )
    outcome_justification = serializers.CharField()


class DecideBudgetSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["Approve", "Reject", "Escalate"])
    justification = serializers.CharField(required=False, allow_blank=True)


class BudgetLineItemsSerializer(serializers.Serializer):
    filing_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    attorney_fees = serializers.DecimalField(max_digits=12, decimal_places=2)
    administrative_costs = serializers.DecimalField(max_digits=12, decimal_places=2)
    threshold_limit = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)


class AssignAttorneySerializer(serializers.Serializer):
    attorney_user_id = serializers.IntegerField()
    institutional_exception = serializers.BooleanField(default=False)


class RespondAttorneyAssignmentSerializer(serializers.Serializer):
    accept = serializers.BooleanField()
    decline_reason = serializers.CharField(required=False, allow_blank=True)


class RecordFilingSerializer(serializers.Serializer):
    external_filing_id = serializers.CharField(max_length=100)
    external_filing_date = serializers.DateField()
    filing_confirmation = serializers.CharField()
    is_international = serializers.BooleanField(default=False)
    international_justification = serializers.CharField(required=False, allow_blank=True)


class RecordGrantSerializer(serializers.Serializer):
    patent_number = serializers.CharField(max_length=100)
    grant_date = serializers.DateField()


class RecordOfficeActionSerializer(serializers.Serializer):
    action_type = serializers.CharField(max_length=100)
    issue_date = serializers.DateField()
    due_date = serializers.DateField()
    details = serializers.CharField()
    requires_applicant_review = serializers.BooleanField(default=True)


class DraftOfficeActionResponseSerializer(serializers.Serializer):
    draft_response = serializers.CharField()


class SubmitOfficeActionResponseSerializer(serializers.Serializer):
    submission_details = serializers.CharField()


class DecideRenewalSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["Renew", "Do Not Renew"])


class RecordMaintenanceActionSerializer(serializers.Serializer):
    transaction_reference = serializers.CharField(max_length=100)


class LicensingRequestCreateSerializer(serializers.Serializer):
    licensee_name = serializers.CharField(max_length=200)
    request_type = serializers.CharField(max_length=50)
    commercial_terms = serializers.CharField()


class LicensingReviewSerializer(serializers.Serializer):
    status = serializers.ChoiceField(
        choices=["under_review", "negotiating", "agreement_recorded", "rejected"]
    )
    negotiation_notes = serializers.CharField(required=False, allow_blank=True)
    agreement_reference = serializers.CharField(required=False, allow_blank=True)


class UploadDocumentSerializer(serializers.Serializer):
    doc_type = serializers.CharField(max_length=50)
    title = serializers.CharField(max_length=200)
    filename = serializers.CharField(max_length=200)
    file_size_bytes = serializers.IntegerField()
    sensitivity = serializers.CharField(default="confidential")
    file_url = serializers.CharField(required=False, allow_blank=True)


class AttachPriorArtSerializer(serializers.Serializer):
    source = serializers.CharField(max_length=100)
    reference_id = serializers.CharField(max_length=100)
    title = serializers.CharField(max_length=300)
    authors = serializers.CharField(required=False, allow_blank=True)
    relevance = serializers.CharField(default="high")
    notes = serializers.CharField(required=False, allow_blank=True)


class LegalAdviceCreateSerializer(serializers.Serializer):
    stage = serializers.CharField(max_length=50)
    advice_text = serializers.CharField()


class PatentabilityAssessmentCreateSerializer(serializers.Serializer):
    recommendation = serializers.ChoiceField(
        choices=["File Patent", "Do Not File", "Needs Amendment"]
    )
    opinion_text = serializers.CharField()
    novelty_score = serializers.IntegerField(default=0)
    non_obviousness_score = serializers.IntegerField(default=0)
    utility_score = serializers.IntegerField(default=0)


class CoInventorConsentWriteSerializer(serializers.Serializer):
    consent_given = serializers.BooleanField(required=False, default=True)
    agreement_signed = serializers.BooleanField(required=False, default=True)
    electronic_signature = serializers.CharField(required=False, allow_blank=True)


class CoInventorWithdrawalConsentWriteSerializer(serializers.Serializer):
    withdrawal_consent_given = serializers.BooleanField(required=False, default=True)


class OfficeActionExtensionSerializer(serializers.Serializer):
    extension_months = serializers.IntegerField(min_value=1, max_value=12, default=1)


class PriorArtSearchResponseSerializer(serializers.Serializer):
    results = serializers.ListField(child=serializers.JSONField())


class PmsReportResponseSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()
    status_distribution = serializers.DictField(child=serializers.IntegerField())
    domain_distribution = serializers.DictField(child=serializers.IntegerField())
