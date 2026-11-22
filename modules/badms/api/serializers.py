from rest_framework import serializers

from modules.badms.models import (
    ArchiveRequest,
    AuditEvent,
    BackupRun,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    SpecialArchiveOperation,
    StorageExtensionRequest,
    StorageThreshold,
)


class ArchiveCreateSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_date = serializers.DateField()
    owners = serializers.JSONField()
    file_type = serializers.CharField(max_length=80)
    reason = serializers.CharField(max_length=4000)
    initial_classification = serializers.ChoiceField(
        choices=["Critical", "Sensitive", "Routine", "Archival"],
        required=False, default="Routine")
    attachment = serializers.FileField()

    def validate_owners(self, value):
        if not isinstance(value, list) or not value or any(
                not isinstance(owner, str) or not owner.strip() or len(owner) > 150
                for owner in value):
            raise serializers.ValidationError("Provide one or more owner names.")
        return [owner.strip() for owner in value]


class ArchiveDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                 default="")


class ClassificationSerializer(serializers.Serializer):
    classification = serializers.ChoiceField(
        choices=["Critical", "Sensitive", "Routine", "Archival"])


class ArchiveReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchiveRequest
        fields = ("id", "user_id", "department", "file_name", "file_date", "owners",
                  "file_type", "reason", "initial_classification", "classification",
                  "status", "decision_note", "checksum_sha256", "created_at", "updated_at")
        read_only_fields = fields


class RestoreCreateSerializer(serializers.Serializer):
    archive_request_id = serializers.IntegerField(min_value=1)


class RestoreReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestorationRequest
        fields = ("id", "archive_request_id", "classification", "status", "outcome",
                  "created_at", "updated_at")
        read_only_fields = fields


class StorageExtensionCreateSerializer(serializers.Serializer):
    requested_bytes = serializers.IntegerField(min_value=1)
    justification = serializers.CharField(max_length=4000)
    attachment = serializers.FileField(required=False)


class StorageExtensionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    note = serializers.CharField(max_length=500, required=False, allow_blank=True,
                                 default="")


class StorageExtensionReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = ("id", "user_id", "department", "requested_bytes", "usage_bytes",
                  "available_bytes", "justification", "status", "decision_note",
                  "created_at", "updated_at")
        read_only_fields = fields


class BackupRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRun
        fields = ("id", "trigger", "status", "dataset", "started_at", "completed_at",
                  "checksum_sha256", "integrity_verified", "outcome")
        read_only_fields = fields


class BackupScheduleSerializer(serializers.ModelSerializer):
    frequency = serializers.ChoiceField(choices=["daily", "weekly"])
    timezone = serializers.CharField(max_length=64)
    class Meta:
        model = BackupSchedule
        fields = ("id", "scope", "dataset", "frequency", "scheduled_time", "timezone",
                  "classifications", "enabled", "updated_at")
        read_only_fields = ("id", "updated_at")


class SpecialArchiveSerializer(serializers.Serializer):
    offline_request_reference = serializers.CharField(max_length=160)
    research_description = serializers.CharField(max_length=4000)
    attachment = serializers.FileField()


class SpecialArchiveReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialArchiveOperation
        fields = ("id", "offline_request_reference", "research_description",
                  "checksum_sha256", "outcome", "created_at")
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = ("id", "actor_user_id", "department", "action", "object_type",
                  "object_id", "outcome", "details", "created_at")
        read_only_fields = fields


class StorageThresholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageThreshold
        fields = ("usage_bytes", "quota_bytes", "is_full", "updated_at")
        read_only_fields = fields


class ArchivePageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = ArchiveReadSerializer(many=True)


class BackupRunPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = BackupRunSerializer(many=True)


class RestorePageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = RestoreReadSerializer(many=True)


class StorageExtensionPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = StorageExtensionReadSerializer(many=True)


class AuditPageSerializer(serializers.Serializer):
    next = serializers.URLField(allow_null=True)
    previous = serializers.URLField(allow_null=True)
    results = AuditEventSerializer(many=True)


class BackupScheduleListSerializer(serializers.Serializer):
    results = BackupScheduleSerializer(many=True)


class MyStorageThresholdSerializer(serializers.Serializer):
    usage_bytes = serializers.IntegerField(min_value=0)
    quota_bytes = serializers.IntegerField(min_value=0, allow_null=True)
    is_full = serializers.BooleanField()
    updated_at = serializers.DateTimeField(allow_null=True)


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityPolicy
        fields = ("retention_days", "updated_by", "updated_at")
        read_only_fields = ("updated_by", "updated_at")

    def validate_retention_days(self, value):
        expected = {choice[0] for choice in ArchiveRequest.CLASSIFICATION}
        if set(value) != expected:
            raise serializers.ValidationError(
                "Provide institute-approved retention days for every classification.")
        if any(type(days) is not int or days < 1 for days in value.values()):
            raise serializers.ValidationError("Retention days must be positive integers.")
        return value
