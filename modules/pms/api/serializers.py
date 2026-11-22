from rest_framework import serializers

from modules.pms.models import (
    Application,
    ApplicationDocument,
    ApplicationInventorAgreement,
    AttorneyAssignment,
    AttorneyProfile,
    BudgetProposal,
    DirectorProfile,
    OfficeActionResponse,
    PatentabilityOpinion,
    PatentAppeal,
    PatentOfficeCommunication,
    PmsAuditEvent,
    PmsConfiguration,
)


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = [
            "id",
            "application_number",
            "applicant_user_id",
            "title",
            "abstract",
            "detailed_description",
            "claims",
            "technical_domain",
            "preferred_attorney_user_id",
            "status",
            "assigned_director_user_id",
            "assigned_attorney_user_id",
            "submitted_at",
            "review_due_at",
            "decision_at",
            "revision_due_at",
            "revision_count",
            "filed_at",
            "grant_date",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "application_number",
            "applicant_user_id",
            "status",
            "assigned_director_user_id",
            "assigned_attorney_user_id",
            "submitted_at",
            "review_due_at",
            "decision_at",
            "revision_due_at",
            "revision_count",
            "filed_at",
            "grant_date",
            "created_at",
            "updated_at",
        ]


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "document_type",
            "sensitivity",
            "original_filename",
            "content_type",
            "size_bytes",
            "version",
            "malware_scan_status",
            "uploaded_at",
        ]
        read_only_fields = fields


class InventorAgreementSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationInventorAgreement
        fields = [
            "id",
            "inventor_id",
            "ownership_percent",
            "agreement_status",
            "consent_recorded_at",
            "signature_reference",
        ]
        read_only_fields = ["id", "consent_recorded_at"]


class AttorneyAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyAssignment
        fields = [
            "id",
            "application_id",
            "attorney_user_id",
            "status",
            "created_at",
            "responded_at",
        ]
        read_only_fields = fields


class BudgetProposalSerializer(serializers.ModelSerializer):
    total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = BudgetProposal
        fields = [
            "id",
            "application_id",
            "filing_fees",
            "attorney_fees",
            "administrative_costs",
            "currency",
            "status",
            "total",
            "availability_checked",
            "decision_by_user_id",
            "decision_justification",
            "decided_at",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "total",
            "availability_checked",
            "decision_by_user_id",
            "decision_justification",
            "decided_at",
            "created_at",
        ]


class PatentabilityOpinionSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentabilityOpinion
        fields = [
            "id",
            "application_id",
            "analysis",
            "novelty",
            "non_obviousness",
            "utility",
            "recommendation",
            "finalized_at",
        ]
        read_only_fields = ["id", "finalized_at"]


class PatentOfficeCommunicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentOfficeCommunication
        fields = [
            "id",
            "application_id",
            "kind",
            "external_reference",
            "received_date",
            "response_due_date",
            "deadline_source",
            "summary",
            "recorded_by_user_id",
            "created_at",
        ]
        read_only_fields = ["id", "recorded_by_user_id", "created_at"]


class OfficeActionResponseSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeActionResponse
        fields = [
            "id",
            "communication_id",
            "response_text",
            "applicant_review_required",
            "status",
            "applicant_decision_by_user_id",
            "applicant_approved_at",
            "submitted_at",
            "external_submission_reference",
        ]
        read_only_fields = [
            "id",
            "status",
            "applicant_decision_by_user_id",
            "applicant_approved_at",
            "submitted_at",
        ]


class PatentAppealSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentAppeal
        fields = [
            "id",
            "application_id",
            "grounds",
            "justification",
            "filed_at",
            "outcome",
            "decision_justification",
            "decided_at",
        ]
        read_only_fields = ["id", "filed_at", "outcome", "decision_justification", "decided_at"]


class PmsAuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = PmsAuditEvent
        fields = [
            "id",
            "actor_user_id",
            "application_id",
            "action",
            "previous_state",
            "new_state",
            "metadata",
            "occurred_at",
        ]
        read_only_fields = fields


class PmsConfigurationSerializer(serializers.ModelSerializer):
    class Meta:
        model = PmsConfiguration
        fields = ["key", "value", "updated_at"]
        read_only_fields = ["updated_at"]


class DirectorProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DirectorProfile
        fields = ["user_id", "expertise_domains", "active", "max_open_reviews"]


class AttorneyProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyProfile
        fields = [
            "user_id",
            "panel_approved",
            "expertise_domains",
            "active",
            "max_open_matters",
            "exception_record",
        ]
