"""Serializers for the SPACS API."""
from __future__ import annotations

from rest_framework import serializers
from modules.spacs.models import (
    CatalogueEntry,
    CataloguePolicyVersion,
    ScholarshipApplication,
    ApplicationDocument,
    ApplicationTransition,
    AwardCycle,
    AwardCandidate,
    SpacsAuditLog,
)


class CataloguePolicyVersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CataloguePolicyVersion
        fields = [
            "id",
            "version_label",
            "effective_from",
            "effective_to",
            "policy_approval_ref",
            "policy_approval_date",
            "application_window_start",
            "application_window_end",
            "is_renewable",
            "renewal_window_start",
            "renewal_window_end",
            "max_renewal_cycles",
            "candidate_source_method",
            "eval_committee_role",
            "approving_authority_title",
            "eligibility_schema",
            "required_evidence_schema",
            "sla_config",
            "is_published",
        ]


class CatalogueEntrySerializer(serializers.ModelSerializer):
    versions = CataloguePolicyVersionSerializer(many=True, read_only=True)
    active_version = serializers.SerializerMethodField()

    class Meta:
        model = CatalogueEntry
        fields = ["id", "code", "title", "kind", "description", "status", "active_version", "versions"]

    def get_active_version(self, obj):
        v = obj.versions.filter(is_published=True).order_by("-effective_from").first()
        return CataloguePolicyVersionSerializer(v).data if v else None


class ApplicationDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationDocument
        fields = [
            "id",
            "doc_type",
            "title",
            "drive_url",
            "drive_file_id",
            "declared_validity_date",
            "is_reused",
            "reused_from_doc_id",
            "verification_status",
            "verification_comment",
        ]
        read_only_fields = ["drive_file_id", "verification_status", "verification_comment"]


class ApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTransition
        fields = ["from_status", "to_status", "actor_user_id", "actor_role_label", "reason", "at"]


class ScholarshipApplicationListSerializer(serializers.ModelSerializer):
    scheme_title = serializers.CharField(source="policy_version.catalogue_entry.title", read_only=True)
    scheme_code = serializers.CharField(source="policy_version.catalogue_entry.code", read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = [
            "id",
            "application_number",
            "user_id",
            "scheme_code",
            "scheme_title",
            "academic_cycle",
            "status",
            "is_renewal",
            "renewal_cycle_number",
            "submitted_at",
            "created_at",
        ]


class ScholarshipApplicationDetailSerializer(serializers.ModelSerializer):
    scheme_title = serializers.CharField(source="policy_version.catalogue_entry.title", read_only=True)
    scheme_code = serializers.CharField(source="policy_version.catalogue_entry.code", read_only=True)
    documents = ApplicationDocumentSerializer(many=True, read_only=True)
    policy_version_detail = CataloguePolicyVersionSerializer(source="policy_version", read_only=True)

    class Meta:
        model = ScholarshipApplication
        fields = [
            "id",
            "application_number",
            "user_id",
            "scheme_code",
            "scheme_title",
            "academic_cycle",
            "status",
            "is_renewal",
            "renewal_cycle_number",
            "prior_award_id",
            "applicant_snapshot",
            "submission_data",
            "documents",
            "submitted_at",
            "verified_at",
            "verification_findings",
            "verification_concern_note",
            "decision_outcome",
            "decision_reason",
            "decision_at",
            "withdrawn_at",
            "withdrawn_reason",
            "policy_version_detail",
            "created_at",
        ]


class DraftSaveInputSerializer(serializers.Serializer):
    policy_version_id = serializers.IntegerField(required=True)
    academic_cycle = serializers.CharField(max_length=20, required=True)
    submission_data = serializers.DictField(required=True)
    documents = serializers.ListField(child=serializers.DictField(), required=False, default=list)
    applicant_snapshot = serializers.DictField(required=False, default=dict)


class ApplicationSubmitInputSerializer(serializers.Serializer):
    student_snapshot = serializers.DictField(required=False, default=dict)


class VerificationActionInputSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["verify", "request_correction", "flag_concern"])
    findings = serializers.DictField(required=False, default=dict)
    comment = serializers.CharField(required=False, allow_blank=True, default="")


class DecisionActionInputSerializer(serializers.Serializer):
    outcome = serializers.ChoiceField(choices=["approved", "rejected", "return_for_correction"])
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    policy_reference = serializers.CharField(required=False, allow_blank=True, default="")


class AwardCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwardCandidate
        fields = [
            "id",
            "award_cycle_id",
            "user_id",
            "source_method",
            "academic_snapshot",
            "nomination_data",
            "is_eligible",
            "ineligibility_notes",
            "evaluation_score",
            "committee_recommendation",
            "committee_remarks",
            "is_final_winner",
        ]


class AwardCycleSerializer(serializers.ModelSerializer):
    award_title = serializers.CharField(source="policy_version.catalogue_entry.title", read_only=True)
    candidates = AwardCandidateSerializer(many=True, read_only=True)

    class Meta:
        model = AwardCycle
        fields = [
            "id",
            "policy_version_id",
            "award_title",
            "convocation_year",
            "status",
            "pool_finalized_at",
            "eval_completed_at",
            "approval_authority_recorded",
            "approval_reference_recorded",
            "approval_recorded_at",
            "published_at",
            "candidates",
            "created_at",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpacsAuditLog
        fields = [
            "id",
            "action",
            "entity_type",
            "entity_id",
            "actor_user_id",
            "actor_role",
            "details",
            "ip_address",
            "created_at",
        ]
