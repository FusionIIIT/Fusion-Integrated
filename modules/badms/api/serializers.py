"""DRF serializers for BADMS endpoints."""
from rest_framework import serializers
from modules.badms.models import (
    BackupOperation,
    BackupSchedule,
    SecureArchivalRequest,
    DataRestorationRequest,
    StorageQuota,
    StorageExtensionRequest,
    BadmsAuditLog,
)


class BackupOperationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupOperation
        fields = "__all__"


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = "__all__"


class SecureArchivalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecureArchivalRequest
        fields = "__all__"


class DataRestorationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataRestorationRequest
        fields = "__all__"


class StorageQuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageQuota
        fields = "__all__"


class StorageExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = "__all__"


class BadmsAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadmsAuditLog
        fields = "__all__"
