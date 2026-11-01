from rest_framework import serializers

from modules.badms.models import ArchiveRequest, AuditEvent, BackupRun


class BackupRunSerializer(serializers.ModelSerializer):
    artifact_url = serializers.SerializerMethodField()

    class Meta:
        model = BackupRun
        fields = ["id", "trigger", "status", "artifact_url", "checksum", "size_bytes",
                  "message", "started_at", "finished_at"]

    def get_artifact_url(self, obj):
        return f"/api/v1/badms/backups/{obj.pk}/download/" if obj.artifact else None


class ArchiveRequestSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(write_only=True, required=True)
    attachment_name = serializers.CharField(source="attachment.name", read_only=True)

    class Meta:
        model = ArchiveRequest
        fields = ["id", "department", "file_name", "data_date", "owners", "file_type",
                  "reason", "attachment", "attachment_name", "initial_classification", "classification",
                  "status", "decision_note", "created_at", "updated_at"]
        read_only_fields = ["classification", "status", "decision_note", "created_at", "updated_at"]

    def validate_file_name(self, value):
        if not value.strip():
            raise serializers.ValidationError("Enter the data name.")
        return value.strip()


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ["id", "actor_id", "action", "object_type", "object_id", "outcome", "details", "created_at"]
