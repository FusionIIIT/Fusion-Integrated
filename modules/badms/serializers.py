"""Serializers for BADMS models."""
from __future__ import annotations

from rest_framework import serializers
from modules.badms.models import (
    ArchivalRequest,
    ArchiveClassification,
    ArchiveStatus,
    BackupExecution,
    BackupSchedule,
    BackupScope,
    BackupType,
    BadmsAuditLog,
    BadmsNotification,
    RestorationRequest,
    RestorationStatus,
    SpecialArchivalRecord,
    StorageExtensionRequest,
    StorageExtensionStatus,
    UserStorageQuota,
)


class UserStorageQuotaSerializer(serializers.ModelSerializer):
    remaining_bytes = serializers.IntegerField(read_only=True)

    class Meta:
        model = UserStorageQuota
        fields = [
            "id",
            "user_id",
            "department",
            "allocated_bytes",
            "used_bytes",
            "remaining_bytes",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ArchivalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalRequest
        fields = [
            "id",
            "user_id",
            "department",
            "file_name",
            "document_date",
            "owners",
            "file_type",
            "file_size_bytes",
            "attachment_path",
            "reason",
            "initial_classification",
            "authoritative_classification",
            "status",
            "checksum",
            "encryption_algorithm",
            "is_encrypted",
            "hod_user_id",
            "hod_comments",
            "hod_decided_at",
            "sysadmin_user_id",
            "sysadmin_comments",
            "sysadmin_classified_at",
            "security_user_id",
            "security_configured_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "department",
            "authoritative_classification",
            "status",
            "checksum",
            "encryption_algorithm",
            "is_encrypted",
            "hod_user_id",
            "hod_comments",
            "hod_decided_at",
            "sysadmin_user_id",
            "sysadmin_comments",
            "sysadmin_classified_at",
            "security_user_id",
            "security_configured_at",
            "created_at",
            "updated_at",
        ]


class ArchivalRequestSubmitSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    document_date = serializers.DateField()
    owners = serializers.ListField(
        child=serializers.CharField(max_length=100),
        required=False,
        default=list,
    )
    file_type = serializers.CharField(max_length=50)
    file_size_bytes = serializers.IntegerField(min_value=0, default=0)
    reason = serializers.CharField()
    initial_classification = serializers.ChoiceField(
        choices=ArchiveClassification.choices,
        default=ArchiveClassification.ROUTINE,
        required=False,
    )
    attachment_path = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")
    checksum = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")


class BadmsAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadmsAuditLog
        fields = [
            "id",
            "actor_user_id",
            "actor_role",
            "action",
            "target_type",
            "target_id",
            "outcome",
            "details",
            "created_at",
        ]
        read_only_fields = fields


class BadmsNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = BadmsNotification
        fields = [
            "id",
            "user_id",
            "recipient_role",
            "subject",
            "message",
            "notification_type",
            "related_object_id",
            "is_read",
            "created_at",
        ]
        read_only_fields = fields


class HodReviewSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class ArchivalClassifySerializer(serializers.Serializer):
    classification = serializers.ChoiceField(choices=ArchiveClassification.choices)
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class ConfigureEncryptionSerializer(serializers.Serializer):
    algorithm = serializers.CharField(max_length=50, default="AES-256-GCM", required=False)
    key_id = serializers.CharField(max_length=100, default="KEY-AES256-SEC-01", required=False)


class BackupExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupExecution
        fields = [
            "id",
            "backup_type",
            "scope",
            "target_dataset",
            "status",
            "started_at",
            "completed_at",
            "size_bytes",
            "checksum",
            "repository_reachable",
            "integrity_verified",
            "error_message",
            "consecutive_failure_count",
            "initiated_by_user_id",
            "metadata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class TriggerBackupSerializer(serializers.Serializer):
    backup_type = serializers.ChoiceField(choices=BackupType.choices, default=BackupType.FULL, required=False)
    scope = serializers.ChoiceField(choices=BackupScope.choices, default=BackupScope.LOCAL, required=False)
    target_dataset = serializers.CharField(max_length=100, default="all", required=False)
    simulate_unreachable = serializers.BooleanField(default=False, required=False)
    simulate_failure = serializers.BooleanField(default=False, required=False)


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = [
            "id",
            "name",
            "schedule_type",
            "target_dataset",
            "frequency",
            "execution_time",
            "classification_filter",
            "is_active",
            "repository_path",
            "created_by_user_id",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_by_user_id", "created_at", "updated_at"]


class RestorationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestorationRequest
        fields = [
            "id",
            "archive_id",
            "backup_id",
            "requester_user_id",
            "target_type",
            "target_name",
            "reason",
            "target_destination",
            "is_sensitive",
            "status",
            "approved_by_user_id",
            "approved_at",
            "restored_at",
            "integrity_verified",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "requester_user_id",
            "is_sensitive",
            "status",
            "approved_by_user_id",
            "approved_at",
            "restored_at",
            "integrity_verified",
            "error_message",
            "created_at",
            "updated_at",
        ]


class SubmitRestorationSerializer(serializers.Serializer):
    archive_id = serializers.IntegerField(required=False, allow_null=True)
    backup_id = serializers.IntegerField(required=False, allow_null=True)
    reason = serializers.CharField()
    target_destination = serializers.CharField(max_length=255, default="/restored", required=False)


class RestorationDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class StorageExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = [
            "id",
            "user_id",
            "department",
            "current_allocated_bytes",
            "requested_bytes",
            "reason",
            "status",
            "hod_user_id",
            "hod_comments",
            "decided_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "user_id",
            "department",
            "current_allocated_bytes",
            "status",
            "hod_user_id",
            "hod_comments",
            "decided_at",
            "created_at",
            "updated_at",
        ]


class SubmitStorageExtensionSerializer(serializers.Serializer):
    requested_bytes = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(min_length=5, max_length=2000)


class StorageExtensionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class SpecialArchivalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialArchivalRecord
        fields = [
            "id",
            "requester_name",
            "requester_designation",
            "dataset_title",
            "classification",
            "offline_media_type",
            "media_serial_number",
            "storage_vault_location",
            "performed_by_user_id",
            "notes",
            "completed_at",
            "checksum",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class SubmitSpecialArchivalSerializer(serializers.Serializer):
    requester_name = serializers.CharField(max_length=150)
    requester_designation = serializers.CharField(max_length=150)
    dataset_title = serializers.CharField(max_length=255)
    classification = serializers.CharField(max_length=50, default="Sensitive Research Data", required=False)
    offline_media_type = serializers.CharField(max_length=100)
    media_serial_number = serializers.CharField(max_length=100)
    storage_vault_location = serializers.CharField(max_length=255)
    notes = serializers.CharField(required=False, allow_blank=True, default="")
    checksum = serializers.CharField(required=False, allow_blank=True, default="")
