"""Serializers for BADMS REST API endpoints.

Explicit allow-lists on write serializers. Never uses `fields = "__all__"`.
"""

from rest_framework import serializers

from modules.badms.models import (
    ArchivalRequest,
    AuditLog,
    BackupRecord,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    SpecialArchivalRecord,
    StorageExtensionRequest,
    UserStorageQuota,
)

# -- Backups & Schedules --


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = (
            "id",
            "name",
            "scope",
            "dataset",
            "frequency",
            "execution_time",
            "classification_filter",
            "repository_path",
            "is_active",
            "created_by_id",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CreateBackupScheduleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=120)
    scope = serializers.ChoiceField(choices=["global", "local"], default="local")
    dataset = serializers.CharField(max_length=80)
    frequency = serializers.ChoiceField(
        choices=["hourly", "daily", "weekly", "monthly"], default="daily"
    )
    execution_time = serializers.CharField(max_length=5, default="02:00")
    classification_filter = serializers.CharField(max_length=30, default="ALL")
    repository_path = serializers.CharField(max_length=255, default="/var/backups/fusion")


class BackupRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRecord
        fields = (
            "id",
            "schedule_id",
            "backup_type",
            "status",
            "trigger_user_id",
            "dataset",
            "repository_path",
            "artifact_path",
            "checksum",
            "size_bytes",
            "is_consistent",
            "error_message",
            "started_at",
            "completed_at",
            "created_at",
        )
        read_only_fields = fields


class TriggerManualBackupSerializer(serializers.Serializer):
    dataset = serializers.CharField(max_length=80, default="all")
    repository_path = serializers.CharField(max_length=255, default="/var/backups/fusion")


# -- Archival Requests --


class ArchivalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalRequest
        fields = (
            "id",
            "user_id",
            "department_id",
            "file_name",
            "file_type",
            "file_size_bytes",
            "owners",
            "reason",
            "attachment_path",
            "initial_classification",
            "authoritative_classification",
            "status",
            "hod_id",
            "hod_decided_at",
            "hod_rejection_reason",
            "classified_by_id",
            "classified_at",
            "security_officer_id",
            "encryption_algorithm",
            "encrypted_archive_path",
            "encryption_configured_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class SubmitArchivalRequestSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=50)
    file_size_bytes = serializers.IntegerField(min_value=1)
    owners = serializers.CharField(max_length=255)
    reason = serializers.CharField()
    attachment_path = serializers.CharField(max_length=500)
    initial_classification = serializers.ChoiceField(
        choices=["critical", "sensitive", "routine", "archival"],
        required=False,
        default="routine",
    )


class HoDDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


class ClassifyArchivalSerializer(serializers.Serializer):
    authoritative_classification = serializers.ChoiceField(
        choices=["critical", "sensitive", "routine", "archival"]
    )


class ConfigureEncryptionSerializer(serializers.Serializer):
    encryption_algorithm = serializers.CharField(max_length=50, default="AES-256")


# -- Special Archival --


class SpecialArchivalRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpecialArchivalRecord
        fields = (
            "id",
            "dataset_name",
            "source_authority",
            "reason",
            "classification",
            "archive_path",
            "performed_by_id",
            "size_bytes",
            "checksum",
            "created_at",
        )
        read_only_fields = fields


class CreateSpecialArchivalSerializer(serializers.Serializer):
    dataset_name = serializers.CharField(max_length=150)
    source_authority = serializers.CharField(max_length=150)
    reason = serializers.CharField()
    archive_path = serializers.CharField(max_length=500)
    size_bytes = serializers.IntegerField(min_value=1)


# -- Storage & Extensions --


class UserStorageQuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStorageQuota
        fields = (
            "user_id",
            "department_id",
            "used_bytes",
            "quota_bytes",
            "is_full",
            "available_infra_bytes",
            "updated_at",
        )
        read_only_fields = fields


class StorageExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = (
            "id",
            "user_id",
            "department_id",
            "requested_bytes",
            "current_usage_bytes",
            "current_quota_bytes",
            "justification",
            "attachment_path",
            "status",
            "hod_id",
            "hod_decided_at",
            "rejection_reason",
            "created_at",
        )
        read_only_fields = fields


class SubmitStorageExtensionSerializer(serializers.Serializer):
    requested_bytes = serializers.IntegerField(min_value=1)
    justification = serializers.CharField()
    attachment_path = serializers.CharField(
        max_length=500, required=False, allow_blank=True, default=""
    )


# -- Restorations --


class RestorationRequestSerializer(serializers.ModelSerializer):
    archival_request = ArchivalRequestSerializer(read_only=True)

    class Meta:
        model = RestorationRequest
        fields = (
            "id",
            "user_id",
            "archival_request_id",
            "archival_request",
            "classification",
            "reason",
            "target_destination",
            "status",
            "sysadmin_id",
            "sysadmin_decided_at",
            "rejection_reason",
            "restored_at",
            "created_at",
        )
        read_only_fields = fields


class SubmitRestorationSerializer(serializers.Serializer):
    archival_request_id = serializers.IntegerField()
    target_destination = serializers.CharField(max_length=255)
    reason = serializers.CharField()


class SysAdminRestorationDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    rejection_reason = serializers.CharField(required=False, allow_blank=True, default="")


# -- Audit, Policies, Notifications --


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = (
            "id",
            "actor_id",
            "actor_username",
            "actor_role",
            "event_source",
            "action",
            "resource_type",
            "resource_id",
            "department_id",
            "outcome",
            "details",
            "ip_address",
            "created_at",
        )
        read_only_fields = fields


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityPolicy
        fields = (
            "id",
            "key",
            "policy_name",
            "encryption_algorithm",
            "is_enforced",
            "parameters",
            "updated_by_id",
            "updated_at",
        )
        read_only_fields = fields


class UpdateSecurityPolicySerializer(serializers.Serializer):
    policy_name = serializers.CharField(max_length=120)
    encryption_algorithm = serializers.CharField(max_length=40, default="AES-256")
    is_enforced = serializers.BooleanField(default=True)
    parameters = serializers.DictField(required=False, default=dict)
