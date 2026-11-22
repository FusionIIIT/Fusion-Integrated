from rest_framework import serializers

from modules.badms.models import (
    ArchivalRequest,
    AuditEvent,
    BackupRecord,
    BackupSchedule,
    RestorationRequest,
    SecurityPolicy,
    StorageExtensionRequest,
    UserStorageQuota,
)


# -- Read Serializers ----------------------------------------------------------
class BackupRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRecord
        fields = (
            "id",
            "backup_type",
            "dataset_name",
            "status",
            "started_at",
            "completed_at",
            "file_path",
            "file_size_bytes",
            "checksum_sha256",
            "error_message",
            "triggered_by_user_id",
            "consecutive_failure_count",
            "created_at",
        )
        read_only_fields = fields


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = (
            "id",
            "name",
            "scope_type",
            "dataset_name",
            "cron_expression",
            "data_classification_filter",
            "is_active",
            "created_by_user_id",
            "version",
            "effective_from",
            "effective_to",
            "last_run_at",
            "next_run_at",
            "created_at",
        )
        read_only_fields = fields


class ArchivalRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivalRequest
        fields = (
            "id",
            "requester_user_id",
            "department",
            "file_name",
            "file_type",
            "file_size_bytes",
            "reason",
            "file_storage_path",
            "initial_classification",
            "authoritative_classification",
            "status",
            "hod_reviewed_by_user_id",
            "hod_decision_at",
            "hod_remarks",
            "sysadmin_classified_by_user_id",
            "classified_at",
            "encryption_algorithm",
            "is_encrypted",
            "encrypted_by_user_id",
            "encrypted_at",
            "is_special_archival",
            "retention_policy_ref",
            "created_at",
        )
        read_only_fields = fields


class StorageExtensionRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = (
            "id",
            "requester_user_id",
            "department",
            "current_usage_bytes",
            "current_quota_bytes",
            "requested_extension_bytes",
            "justification",
            "status",
            "hod_reviewed_by_user_id",
            "hod_decision_at",
            "hod_remarks",
            "created_at",
        )
        read_only_fields = fields


class UserStorageQuotaSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStorageQuota
        fields = (
            "id",
            "user_id",
            "allocated_quota_bytes",
            "used_storage_bytes",
            "is_full",
            "last_calculated_at",
        )
        read_only_fields = fields


class RestorationRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = RestorationRequest
        fields = (
            "id",
            "requester_user_id",
            "department",
            "archival_request_id",
            "classification",
            "target_destination",
            "status",
            "approved_by_user_id",
            "approved_at",
            "executed_by_user_id",
            "restored_at",
            "error_message",
            "created_at",
        )
        read_only_fields = fields


class AuditEventSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEvent
        fields = (
            "id",
            "event_type",
            "actor_user_id",
            "actor_role",
            "target_model",
            "target_id",
            "department",
            "details",
            "ip_address",
            "timestamp",
        )
        read_only_fields = fields


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityPolicy
        fields = (
            "id",
            "policy_key",
            "policy_value",
            "configured_by_user_id",
            "effective_from",
            "effective_to",
            "is_active",
            "created_at",
        )
        read_only_fields = fields


class DepartmentReportSerializer(serializers.Serializer):
    department = serializers.CharField()
    total_archival_requests = serializers.IntegerField()
    archival_by_status = serializers.DictField()
    total_storage_extensions = serializers.IntegerField()
    storage_by_status = serializers.DictField()


# -- Write / Action Serializers ------------------------------------------------
class TriggerManualBackupSerializer(serializers.Serializer):
    dataset_name = serializers.CharField(max_length=100)


class CreateBackupScheduleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150)
    dataset_name = serializers.CharField(max_length=100)
    cron_expression = serializers.CharField(max_length=100)
    data_classification_filter = serializers.CharField(max_length=50, required=False, default="")


class UpdateBackupScheduleSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    cron_expression = serializers.CharField(max_length=100, required=False)
    data_classification_filter = serializers.CharField(max_length=50, required=False)


class SubmitArchivalRequestSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=100, required=False, default="")
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=50)
    file_size_bytes = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()
    file_storage_path = serializers.CharField(max_length=500)
    initial_classification = serializers.ChoiceField(
        choices=["Routine", "Sensitive", "Critical", "Archival"], required=False, default="Routine"
    )


class DecideArchivalRequestSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ClassifyArchivalRequestSerializer(serializers.Serializer):
    classification = serializers.ChoiceField(
        choices=["Routine", "Sensitive", "Critical", "Archival"]
    )


class ConfigureEncryptionSerializer(serializers.Serializer):
    encryption_algorithm = serializers.CharField(
        max_length=50, required=False, default="AES-256-GCM"
    )


class SpecialArchivalSerializer(serializers.Serializer):
    file_name = serializers.CharField(max_length=255)
    file_type = serializers.CharField(max_length=50)
    file_size_bytes = serializers.IntegerField(min_value=1)
    reason = serializers.CharField()
    file_storage_path = serializers.CharField(max_length=500)
    classification = serializers.ChoiceField(
        choices=["Routine", "Sensitive", "Critical", "Archival"], required=False, default="Archival"
    )


class SubmitStorageExtensionSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=100, required=False, default="")
    requested_extension_bytes = serializers.IntegerField(min_value=1)
    justification = serializers.CharField()


class DecideStorageExtensionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class RequestRestorationSerializer(serializers.Serializer):
    archival_request_id = serializers.IntegerField(min_value=1)
    target_destination = serializers.CharField(max_length=255)


class ApproveSensitiveRestorationSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])


class SaveSecurityPolicySerializer(serializers.Serializer):
    policy_key = serializers.CharField(max_length=100)
    policy_value = serializers.DictField()
