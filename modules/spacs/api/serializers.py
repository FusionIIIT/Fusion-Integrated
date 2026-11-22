"""Serializers for the SPACS API."""
from __future__ import annotations

from drf_spectacular.utils import extend_schema_field
from rest_framework import serializers

from modules.spacs.models import (
    ApplicationDocument,
    ApplicationTransition,
    AwardCandidate,
    AwardCycle,
    ScholarshipApplication,
    SchemeCatalogue,
    SchemePolicyVersion,
    SpacsAuditLog,
    SpacsNotification,
)


class SchemePolicyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = SchemePolicyVersion
        fields = [
            "id",
            "version_number",
            "title",
            "description",
            "eligibility_criteria",
            "required_documents",
            "candidate_source_method",
            "is_renewable",
            "renewal_rules",
            "policy_approval_reference",
            "policy_approved_by",
            "effective_from",
            "effective_to",
            "application_window_start",
            "application_window_end",
            "renewal_window_start",
            "renewal_window_end",
            "sla_verification_days",
            "sla_decision_days",
            "status",
            "created_at",
        ]


class SchemeCatalogueSerializer(serializers.ModelSerializer):
    versions = SchemePolicyVersionSerializer(many=True, read_only=True)
    active_version = serializers.SerializerMethodField()

    class Meta:
        model = SchemeCatalogue
        fields = [
            "id",
            "code",
            "name",
            "scheme_type",
            "description",
            "status",
            "retired_at",
            "retired_reason",
            "versions",
            "active_version",
            "created_at",
        ]

    @extend_schema_field(SchemePolicyVersionSerializer)
    def get_active_version(self, obj):
        v = obj.versions.filter(status="published").order_by("-version_number").first()
        return SchemePolicyVersionSerializer(v).data if v else None


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "application_id",
            "student_user_id",
            "doc_type",
            "title",
            "file_url",
            "valid_until",
            "is_reused",
            "reused_from_doc_id",
            "verification_status",
            "verification_notes",
            "verified_by_user_id",
            "verified_at",
            "created_at",
        ]


class ApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTransition
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "actor_role",
            "reason",
            "at",
        ]


class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source="scheme.code", read_only=True)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    transitions = ApplicationTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = [
            "id",
            "application_number",
            "student_user_id",
            "scheme_id",
            "scheme_code",
            "scheme_name",
            "policy_version_id",
            "academic_cycle",
            "is_renewal",
            "prior_application_id",
            "status",
            "application_data",
            "eligibility_snapshot",
            "submitted_at",
            "assigned_assistant_user_id",
            "verification_findings",
            "verification_concern_details",
            "correction_requested_reason",
            "correction_requested_at",
            "resubmitted_at",
            "verified_at",
            "verified_by_user_id",
            "decision_outcome",
            "decision_reason",
            "decided_at",
            "decided_by_user_id",
            "withdrawn_at",
            "withdrawal_reason",
            "documents",
            "transitions",
            "created_at",
            "updated_at",
        ]


class ScholarshipApplicationCreateSerializer(serializers.Serializer):
    scheme_id = serializers.IntegerField()
    academic_cycle = serializers.CharField(max_length=32)
    application_data = serializers.DictField(required=False, default=dict)
    submit = serializers.BooleanField(required=False, default=False)
    facts = serializers.DictField(required=False, default=dict)


class ScholarshipApplicationModifySerializer(serializers.Serializer):
    application_data = serializers.DictField(required=False, default=dict)
    resubmit = serializers.BooleanField(required=False, default=False)


class ScholarshipApplicationWithdrawSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ScholarshipApplicationVerifySerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["start", "verify", "request_correction", "record_concern"])
    findings = serializers.DictField(required=False, default=dict)
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ScholarshipApplicationDecideSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject", "return_correction"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class ScholarshipRenewalSerializer(serializers.Serializer):
    prior_application_id = serializers.IntegerField()
    academic_cycle = serializers.CharField(max_length=32)
    renewal_data = serializers.DictField(required=False, default=dict)
    facts = serializers.DictField(required=False, default=dict)


class ApplicationSubmitSerializer(serializers.Serializer):
    application_data = serializers.DictField(required=False, default=dict)
    facts = serializers.DictField(required=False, default=dict)


class DocumentUploadSerializer(serializers.Serializer):
    doc_type = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=255, required=False, default="")
    file_url = serializers.CharField(max_length=512)
    valid_until = serializers.DateField(required=False, allow_null=True)


class DocumentReuseSerializer(serializers.Serializer):
    source_doc_id = serializers.IntegerField()


class AwardCycleCreateSerializer(serializers.Serializer):
    scheme_id = serializers.IntegerField()
    academic_cycle = serializers.CharField(max_length=32)
    convocation_year = serializers.IntegerField()
    evaluating_body = serializers.CharField(max_length=255)
    committee_members = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class AwardCandidatePoolSerializer(serializers.Serializer):
    candidates = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class AwardEvaluationSerializer(serializers.Serializer):
    evaluations = serializers.ListField(child=serializers.DictField(), required=False, default=list)


class AwardApprovalSerializer(serializers.Serializer):
    approval_reference = serializers.CharField(max_length=255, required=False, default="")
    approving_authority = serializers.CharField(max_length=255, required=False, default="")
    approved_candidate_ids = serializers.ListField(
        child=serializers.IntegerField(), required=False, default=list
    )


class CatalogueRetireSerializer(serializers.Serializer):
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class AwardCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwardCandidate
        fields = [
            "id",
            "award_cycle_id",
            "student_user_id",
            "source_method",
            "cpi",
            "discipline",
            "merit_data",
            "is_shortlisted",
            "evaluation_score",
            "evaluation_remarks",
            "recommendation_status",
            "final_outcome",
            "created_at",
        ]


class AwardCycleSerializer(serializers.ModelSerializer):
    scheme_code = serializers.CharField(source="scheme.code", read_only=True)
    scheme_name = serializers.CharField(source="scheme.name", read_only=True)
    candidates = AwardCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = AwardCycle
        fields = [
            "id",
            "scheme_id",
            "scheme_code",
            "scheme_name",
            "policy_version_id",
            "academic_cycle",
            "convocation_year",
            "status",
            "evaluating_body",
            "committee_members",
            "approving_authority",
            "approval_reference",
            "approval_recorded_at",
            "published_at",
            "candidates",
            "created_at",
        ]


class SpacsNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacsNotification
        fields = [
            "id",
            "recipient_user_id",
            "recipient_role",
            "event_type",
            "title",
            "message",
            "reference_id",
            "is_read",
            "created_at",
        ]


class SpacsAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacsAuditLog
        fields = [
            "id",
            "actor_user_id",
            "actor_role",
            "action",
            "entity_type",
            "entity_id",
            "details",
            "ip_address",
            "timestamp",
        ]
