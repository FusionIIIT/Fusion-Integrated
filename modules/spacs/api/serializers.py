from rest_framework import serializers

from modules.spacs.models import (
    Application,
    ApplicationEvidence,
    AwardCandidate,
    AwardCycle,
    CatalogueVersion,
    WorkflowTask,
)


class CatalogueVersionSerializer(serializers.ModelSerializer):
    entry_kind = serializers.CharField(source="entry.kind", read_only=True)

    class Meta:
        model = CatalogueVersion
        fields = (
            "id",
            "entry_id",
            "entry_kind",
            "version_number",
            "configuration",
            "effective_from",
            "effective_to",
            "application_opens_at",
            "application_closes_at",
            "status",
        )
        read_only_fields = fields


class ApplicationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Application
        fields = (
            "public_id",
            "user_id",
            "catalogue_version",
            "kind",
            "academic_cycle",
            "state",
            "application_data",
            "submitted_at",
            "created_at",
        )
        read_only_fields = fields


class ApplicationStartSerializer(serializers.Serializer):
    catalogue_version_id = serializers.IntegerField(min_value=1)
    academic_cycle = serializers.CharField(max_length=100, allow_blank=False)


class ApplicationDraftSerializer(serializers.Serializer):
    application_data = serializers.DictField(
        child=serializers.JSONField(allow_null=True),
        allow_empty=True,
    )


class ApplicationReviewSerializer(serializers.Serializer):
    findings = serializers.DictField(
        child=serializers.JSONField(allow_null=True),
        allow_empty=True,
    )


class WorkflowReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(allow_blank=False, trim_whitespace=True)


class WorkflowDecisionSerializer(serializers.Serializer):
    reason = serializers.CharField(
        required=False,
        default="",
        allow_blank=True,
        trim_whitespace=True,
    )


class VerificationRouteSerializer(serializers.Serializer):
    concern = serializers.BooleanField(default=False)


class EvidenceUploadSerializer(serializers.Serializer):
    requirement_id = serializers.CharField(max_length=100, allow_blank=False)
    file = serializers.FileField()


class EvidenceReuseSerializer(serializers.Serializer):
    evidence_id = serializers.IntegerField(min_value=1)
    requirement_id = serializers.CharField(max_length=100, allow_blank=False)


class EvidenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationEvidence
        fields = ("id", "requirement_id", "metadata", "created_at")
        read_only_fields = fields


class AwardCycleStartSerializer(serializers.Serializer):
    catalogue_version_id = serializers.IntegerField(min_value=1)
    candidate_source = serializers.ChoiceField(
        choices=[value for value, _ in AwardCycle.SOURCE_METHODS],
    )


class AwardCandidateInputSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    source_reference = serializers.DictField(
        child=serializers.JSONField(allow_null=True),
        required=False,
        default=dict,
    )


class AwardCandidateBatchSerializer(serializers.Serializer):
    candidates = AwardCandidateInputSerializer(many=True, allow_empty=False)


class AwardCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwardCycle
        fields = (
            "id",
            "catalogue_version",
            "candidate_source",
            "state",
            "created_at",
        )
        read_only_fields = fields


class AwardCandidateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AwardCandidate
        fields = (
            "id",
            "cycle",
            "user_id",
            "source",
            "source_reference",
            "added_by_user_id",
            "created_at",
        )
        read_only_fields = fields


class WorkflowTaskSerializer(serializers.ModelSerializer):
    application = ApplicationSerializer(read_only=True)
    review_findings = serializers.SerializerMethodField()
    policy_configuration = serializers.SerializerMethodField()
    evidence = serializers.SerializerMethodField()

    class Meta:
        model = WorkflowTask
        fields = (
            "id",
            "role_name",
            "assigned_user_id",
            "created_at",
            "application",
            "review_findings",
            "policy_configuration",
            "evidence",
        )
        read_only_fields = fields

    def get_review_findings(self, task):
        application = task.application
        reviews = application.reviews.all()
        if application.submitted_at is not None:
            reviews = reviews.filter(at__gte=application.submitted_at)
        return [
            {"reviewer_user_id": row.reviewer_user_id, "findings": row.findings, "at": row.at}
            for row in reviews
        ]

    def get_policy_configuration(self, task):
        return task.application.catalogue_version.configuration

    def get_evidence(self, task):
        return EvidenceSerializer(
            task.application.evidence.order_by("created_at", "id"),
            many=True,
        ).data
