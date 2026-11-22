"""DRF serializers for patents API (Step 4.5)."""
from __future__ import annotations

from rest_framework import serializers

from modules.patents.models import (
    AppealRecord,
    ApplicationDocument,
    AttorneyPanelMember,
    CoInventor,
    OfficeActionRecord,
    PatentApplication,
    PatentBudgetLedger,
    ReviewDecision,
    TechnologyTransferRecord,
)


class CoInventorSerializer(serializers.ModelSerializer):
    class Meta:
        model = CoInventor
        fields = [
            "id",
            "user_id",
            "name",
            "email",
            "share_percentage",
            "consent_granted",
            "consent_timestamp",
        ]


class CoInventorInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(required=False, allow_null=True)
    name = serializers.CharField(max_length=255)
    email = serializers.EmailField()
    share_percentage = serializers.DecimalField(max_digits=5, decimal_places=2)


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "document_type",
            "file_name",
            "file_format",
            "file_size_bytes",
            "sensitivity_level",
            "version",
            "uploaded_by_user_id",
            "created_at",
        ]


class ReviewDecisionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ReviewDecision
        fields = [
            "id",
            "director_user_id",
            "decision",
            "justification",
            "assigned_at",
            "decided_at",
        ]


class AppealRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppealRecord
        fields = [
            "id",
            "applicant_user_id",
            "grounds",
            "status",
            "director_user_id",
            "decision_notes",
            "submitted_at",
            "decided_at",
        ]


class PatentBudgetLedgerSerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentBudgetLedger
        fields = [
            "id",
            "entry_type",
            "amount",
            "currency",
            "category",
            "status",
            "authorized_by_user_id",
            "notes",
            "created_at",
        ]


class OfficeActionRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = OfficeActionRecord
        fields = [
            "id",
            "action_code",
            "issuing_authority",
            "issued_date",
            "response_deadline",
            "status",
            "requires_applicant_review",
            "response_summary",
            "submitted_at",
        ]


class TechnologyTransferRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = TechnologyTransferRecord
        fields = [
            "id",
            "applicant_user_id",
            "request_type",
            "partner_name",
            "status",
            "confidentiality_level",
            "terms_summary",
            "created_at",
        ]


class AttorneyPanelMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = AttorneyPanelMember
        fields = [
            "id",
            "user_id",
            "firm_name",
            "expertise_domains",
            "active_workload",
            "is_approved_panel",
        ]


class PatentApplicationSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = PatentApplication
        fields = [
            "id",
            "application_number",
            "user_id",
            "title",
            "status",
            "domain_category",
            "assigned_director_id",
            "assigned_attorney_id",
            "external_filing_id",
            "jurisdiction",
            "version",
            "created_at",
            "updated_at",
        ]


class PatentApplicationDetailSerializer(serializers.ModelSerializer):
    co_inventors = CoInventorSerializer(many=True, read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    reviews = ReviewDecisionSerializer(many=True, read_only=True)
    appeals = AppealRecordSerializer(many=True, read_only=True)
    budget_entries = PatentBudgetLedgerSerializer(many=True, read_only=True)
    office_actions = OfficeActionRecordSerializer(many=True, read_only=True)
    licensing_records = TechnologyTransferRecordSerializer(many=True, read_only=True)

    class Meta:
        model = PatentApplication
        fields = [
            "id",
            "application_number",
            "user_id",
            "title",
            "abstract",
            "description",
            "claims",
            "status",
            "domain_category",
            "assigned_director_id",
            "assigned_attorney_id",
            "external_filing_id",
            "filing_date",
            "grant_date",
            "jurisdiction",
            "decision_date",
            "version",
            "co_inventors",
            "documents",
            "reviews",
            "appeals",
            "budget_entries",
            "office_actions",
            "licensing_records",
            "created_at",
            "updated_at",
        ]


# -- Request Input & Utility Serializers ----------------------------------------

class CreateApplicationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500)
    abstract = serializers.CharField()
    description = serializers.CharField()
    claims = serializers.CharField()
    domain_category = serializers.CharField(max_length=100, required=False, default="")
    jurisdiction = serializers.CharField(max_length=50, required=False, default="IN")
    co_inventors = CoInventorInputSerializer(many=True, required=False, default=list)


class UpdateApplicationSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=500, required=False)
    abstract = serializers.CharField(required=False)
    description = serializers.CharField(required=False)
    claims = serializers.CharField(required=False)
    domain_category = serializers.CharField(max_length=100, required=False)


class AssignDirectorSerializer(serializers.Serializer):
    director_id = serializers.IntegerField()


class ReviewDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT", "NEEDS_REVISION"])
    justification = serializers.CharField(min_length=50)


class AssignAttorneySerializer(serializers.Serializer):
    attorney_id = serializers.IntegerField()


class AppealInputSerializer(serializers.Serializer):
    grounds = serializers.CharField()


class AppealDecisionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["REMAND", "UPHOLD", "MODIFY"])
    notes = serializers.CharField(required=False, default="")


class PatentWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField()


class FilingInputSerializer(serializers.Serializer):
    external_filing_id = serializers.CharField(max_length=100, required=False)


class BudgetDecisionInputSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    notes = serializers.CharField(required=False, default="")


class OfficeActionInputSerializer(serializers.Serializer):
    action_code = serializers.CharField(max_length=100)
    issuing_authority = serializers.CharField(max_length=100)
    issued_date = serializers.DateField()
    response_deadline = serializers.DateField()
    requires_applicant_review = serializers.BooleanField(required=False, default=False)


class OfficeActionResponseInputSerializer(serializers.Serializer):
    response_summary = serializers.CharField()


class TechTransferInputSerializer(serializers.Serializer):
    application_id = serializers.IntegerField()
    request_type = serializers.CharField(max_length=50)
    partner_name = serializers.CharField(max_length=255)
    terms_summary = serializers.CharField(required=False, default="")


class RenewalDecisionInputSerializer(serializers.Serializer):
    renew = serializers.BooleanField()
    notes = serializers.CharField(required=False, default="")


class ConsentResponseSerializer(serializers.Serializer):
    consent_recorded = serializers.BooleanField()


class AssessmentInputSerializer(serializers.Serializer):
    action = serializers.CharField(default="start")


class RespondAssignmentInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"], default="accept")


class DocumentUploadInputSerializer(serializers.Serializer):
    document_type = serializers.CharField(max_length=50, default="specification")
    file_name = serializers.CharField(max_length=255, default="document.pdf")


class PriorArtInputSerializer(serializers.Serializer):
    query = serializers.CharField()


class PriorArtResultSerializer(serializers.Serializer):
    query = serializers.CharField()
    results = serializers.ListField(child=serializers.CharField())


class ReportsResponseSerializer(serializers.Serializer):
    total_applications = serializers.IntegerField()
    filed_count = serializers.IntegerField()
    granted_count = serializers.IntegerField()


class AuditLogsResponseSerializer(serializers.Serializer):
    audit_logs = serializers.ListField(child=serializers.CharField())


class ConsentConfirmSerializer(serializers.Serializer):
    token = serializers.CharField(max_length=200)


class ConsentTokenIssuedSerializer(serializers.Serializer):
    sent = serializers.BooleanField()
