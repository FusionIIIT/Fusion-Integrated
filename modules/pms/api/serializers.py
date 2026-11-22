from rest_framework import serializers

from modules.pms.models.application import PatentApplication
from modules.pms.models.audit import PatentAuditEvent
from modules.pms.models.budget import PatentBudget
from modules.pms.models.documents import PatentDocumentVersion
from modules.pms.models.finance import PatentFinancialTransaction
from modules.pms.models.inventors import CoInventor, PriorArtReference
from modules.pms.models.maintenance import MaintenanceRenewal
from modules.pms.models.office_action import OfficeAction
from modules.pms.models.reviews import InternalReview


class CoInventorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoInventor
        fields = [
            "id",
            "user_id",
            "inventor_name",
            "affiliation",
            "contribution_percentage",
            "agreement_signed",
            "agreement_signed_at",
        ]


class PriorArtReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = PriorArtReference
        fields = [
            "id",
            "title",
            "citation_type",
            "publication_number_or_doi",
            "relevance_summary",
            "attached_file_drive_link",
        ]


class InternalReviewSerializer(serializers.ModelSerializer):
    class Meta:
        model = InternalReview
        fields = [
            "id",
            "reviewer_user_id",
            "review_stage",
            "verdict",
            "comments",
            "novelty_score",
            "inventive_step_score",
            "commercial_viability_score",
            "created_at",
        ]


class PatentBudgetSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentBudget
        fields = [
            "id",
            "estimated_filing_fee",
            "estimated_attorney_fee",
            "estimated_search_fee",
            "total_estimated_amount",
            "approved_amount",
            "budget_status",
            "decided_by_user_id",
            "decision_date",
            "escalation_notes",
        ]


class PatentFinancialTransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentFinancialTransaction
        fields = [
            "id",
            "transaction_type",
            "amount",
            "currency",
            "payment_status",
            "reference_no",
            "recorded_by_user_id",
            "effective_date",
            "description",
            "created_at",
        ]


class OfficeActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeAction
        fields = [
            "id",
            "action_type",
            "issuing_authority",
            "issue_date",
            "statutory_deadline",
            "objections_summary",
            "response_draft",
            "response_status",
            "response_submitted_date",
            "handled_by_attorney_id",
        ]


class MaintenanceRenewalSerializer(serializers.ModelSerializer):
    class Meta:
        model = MaintenanceRenewal
        fields = [
            "id",
            "renewal_year",
            "due_date",
            "grace_period_deadline",
            "annuity_fee",
            "decision",
            "decided_by_user_id",
            "payment_reference",
        ]


class PatentDocumentVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentDocumentVersion
        fields = [
            "id",
            "doc_type",
            "version_number",
            "title",
            "drive_link",
            "uploaded_by_user_id",
            "created_at",
        ]


class PatentAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentAuditEvent
        fields = [
            "id",
            "event_name",
            "from_status",
            "to_status",
            "actor_user_id",
            "payload",
            "created_at",
        ]


class PatentApplicationSerializer(serializers.ModelSerializer):
    inventors = CoInventorSerializer(many=True, read_only=True)
    prior_art_references = PriorArtReferenceSerializer(many=True, read_only=True)
    budget = PatentBudgetSerializer(read_only=True)

    class Meta:
        model = PatentApplication
        fields = [
            "id",
            "application_no",
            "title",
            "abstract",
            "detailed_description",
            "claims",
            "field_of_invention",
            "applicant_user_id",
            "status",
            "filing_type",
            "official_filing_number",
            "official_filing_date",
            "grant_number",
            "grant_date",
            "assigned_director_id",
            "assigned_attorney_id",
            "inventors",
            "prior_art_references",
            "budget",
            "created_at",
            "updated_at",
        ]
