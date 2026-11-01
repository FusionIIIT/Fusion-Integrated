"""SPACS serializers with explicit writable fields and ownership safeguards."""
from rest_framework import serializers

from modules.spacs.models import ScholarshipApplication, SupportingDocument


class ScholarshipApplicationSerializer(serializers.ModelSerializer):
    student_id = serializers.IntegerField()
    status = serializers.ChoiceField(
        choices=ScholarshipApplication.STATUS_CHOICES,
        default=ScholarshipApplication.STATUS_DRAFT,
    )
    documents_list = serializers.ListField(
        child=serializers.CharField(max_length=64, allow_blank=False),
        required=False,
        default=list,
    )

    class Meta:
        model = ScholarshipApplication
        fields = (
            "application_id",
            "scheme_id",
            "student_id",
            "submission_date",
            "status",
            "documents_list",
            "assigned_assistant_user_id",
            "verification_status",
            "verification_findings",
            "verified_by_user_id",
            "verified_at",
            "decision_note",
            "decided_by_user_id",
            "decided_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "application_id",
            "assigned_assistant_user_id",
            "verified_by_user_id",
            "verified_at",
            "decided_by_user_id",
            "decided_at",
            "created_at",
            "updated_at",
        )

    def get_fields(self):
        fields = super().get_fields()
        if self.instance is not None:
            fields["student_id"].read_only = True
        return fields

    def validate_documents_list(self, value):
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "Document identifiers must not contain duplicates."
            )
        return value


class SupportingDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = SupportingDocument
        fields = (
            "document_id",
            "document_type",
            "file_url",
            "upload_date",
            "is_reusable",
            "validity_status",
            "owner_user_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = (
            "document_id",
            "owner_user_id",
            "created_at",
            "updated_at",
        )
