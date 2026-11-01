"""DRF Serializers for BADMS endpoints."""

from rest_framework import serializers
from ..models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    EncryptedArchive,
    RestorationRequest,
    StorageExtensionRequest,
    StorageQuota,
)


class BackupRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRecord
        fields = "__all__"


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = "__all__"


class StorageQuotaSerializer(serializers.ModelSerializer):
    usage_percentage = serializers.ReadOnlyField()

    class Meta:
        model = StorageQuota
        fields = "__all__"


class EncryptedArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = EncryptedArchive
        fields = "__all__"


class ArchivalRequestSerializer(serializers.ModelSerializer):
    encrypted_archive = EncryptedArchiveSerializer(read_only=True)

    class Meta:
        model = ArchivalRequest
        fields = "__all__"


class StorageExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = "__all__"


class RestorationRequestSerializer(serializers.ModelSerializer):
    archival_file_name = serializers.CharField(source="archival_request.file_name", read_only=True)

    class Meta:
        model = RestorationRequest
        fields = "__all__"


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = "__all__"
