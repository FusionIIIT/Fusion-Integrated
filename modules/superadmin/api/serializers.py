from __future__ import annotations

from rest_framework import serializers

from modules.superadmin.models.archival import (
    ArchivedUserRecord,
    HistoricalDataArchive,
    PurgeRequest,
)
from modules.superadmin.models.audit import SuperAdminAuditLog
from modules.superadmin.models.config import SystemPolicyParameter


class DashboardSummarySerializer(serializers.Serializer):
    archived_users_reversible = serializers.IntegerField()
    archived_users_total = serializers.IntegerField()
    purge_requests_pending = serializers.IntegerField()
    audit_logs_total = serializers.IntegerField()


class ArchivedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedUserRecord
        fields = (
            "user_id",
            "institute_id",
            "username",
            "email",
            "user_kind",
            "status",
            "archived_at",
            "reversible_until",
            "authorized_by",
            "archival_reason",
            "restored_at",
            "restored_by",
            "restoration_reason",
            "finalized_permanent_at",
            "metadata_snapshot",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class ArchiveUserCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    institute_id = serializers.CharField(max_length=32)
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    user_kind = serializers.CharField(max_length=16)
    is_deactivated = serializers.BooleanField(default=True)
    deactivated_at = serializers.DateTimeField(required=False, allow_null=True, default=None)
    has_pending_transactions = serializers.BooleanField(default=False)
    archival_reason = serializers.CharField()
    metadata_snapshot = serializers.JSONField(required=False, default=dict)


class RestoreUserSerializer(serializers.Serializer):
    restoration_reason = serializers.CharField()


class HistoricalArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalDataArchive
        fields = (
            "id",
            "dataset_category",
            "title",
            "date_range_start",
            "date_range_end",
            "record_count",
            "backup_file_path",
            "backup_checksum",
            "retention_expires_at",
            "is_restored",
            "restored_at",
            "is_purged",
            "archived_by",
            "summary_metadata",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class HistoricalArchiveCreateSerializer(serializers.Serializer):
    dataset_category = serializers.CharField(max_length=64)
    title = serializers.CharField(max_length=200)
    date_range_start = serializers.DateField()
    date_range_end = serializers.DateField()
    record_count = serializers.IntegerField(min_value=1)
    backup_file_path = serializers.CharField(max_length=255)
    backup_checksum = serializers.CharField(max_length=64)
    retention_expires_at = serializers.DateField()
    summary_metadata = serializers.JSONField(required=False, default=dict)


class PurgeRequestSerializer(serializers.ModelSerializer):
    archive_title = serializers.CharField(source="archive.title", read_only=True)
    dataset_category = serializers.CharField(source="archive.dataset_category", read_only=True)

    class Meta:
        model = PurgeRequest
        fields = (
            "id",
            "archive",
            "archive_title",
            "dataset_category",
            "status",
            "requested_by",
            "requested_at",
            "request_reason",
            "it_head_id",
            "it_head_decision_at",
            "it_head_comments",
            "purged_at",
            "execution_summary",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PurgeRequestCreateSerializer(serializers.Serializer):
    archive_id = serializers.IntegerField()
    request_reason = serializers.CharField()


class PurgeDecisionSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    comments = serializers.CharField(required=False, default="", allow_blank=True)


class PurgeExecuteSerializer(serializers.Serializer):
    reauth_token = serializers.CharField(required=False, allow_blank=True)
    execution_summary = serializers.JSONField(required=False, default=dict)


class PolicyParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemPolicyParameter
        fields = (
            "id",
            "key",
            "value",
            "value_type",
            "version",
            "effective_from",
            "effective_to",
            "description",
            "updated_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class PolicySupersedeSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=64)
    value = serializers.CharField(max_length=255)
    value_type = serializers.CharField(max_length=16, default="string")
    description = serializers.CharField(required=False, default="", allow_blank=True)


class SuperAdminAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdminAuditLog
        fields = (
            "id",
            "timestamp",
            "actor_id",
            "actor_username",
            "actor_role",
            "action",
            "target_id",
            "target_type",
            "result",
            "ip_address",
            "user_agent",
            "reason",
            "context_metadata",
        )
        read_only_fields = fields
