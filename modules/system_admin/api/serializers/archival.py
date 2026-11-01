"""Archival serializers for System Admin module."""
from rest_framework import serializers

from modules.system_admin.models import ArchivedRecord, PurgeRequest


class ArchivedRecordReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedRecord
        fields = [
            "id",
            "category",
            "identifier",
            "data_payload",
            "retention_until",
            "backup_reference",
            "archived_at",
            "archived_by_user_id",
            "reason",
            "status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PurgeRequestReadSerializer(serializers.ModelSerializer):
    archive_category = serializers.CharField(source="archived_record.category", read_only=True)
    archive_identifier = serializers.CharField(source="archived_record.identifier", read_only=True)
    archive_retention_until = serializers.DateField(source="archived_record.retention_until", read_only=True)

    class Meta:
        model = PurgeRequest
        fields = [
            "id",
            "archived_record_id",
            "archive_category",
            "archive_identifier",
            "archive_retention_until",
            "requested_by_user_id",
            "requested_at",
            "reason",
            "status",
            "it_head_user_id",
            "authorized_at",
            "rejection_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class ArchiveUserRequestSerializer(serializers.Serializer):
    retention_years = serializers.IntegerField(default=7)
    reversible_window_days = serializers.IntegerField(default=180)
    reason = serializers.CharField(required=True)
    reauthenticated = serializers.BooleanField(default=True)


class RestoreUserRequestSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)
    reauthenticated = serializers.BooleanField(default=True)


class ArchiveHistoricalDataSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=64)
    identifier = serializers.CharField(max_length=128)
    data_payload = serializers.DictField()
    retention_years = serializers.IntegerField(default=7)
    backup_reference = serializers.CharField(required=False, allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)
    reauthenticated = serializers.BooleanField(default=True)


class RequestPurgeSerializer(serializers.Serializer):
    archive_id = serializers.IntegerField()
    reason = serializers.CharField(required=True)
    reauthenticated = serializers.BooleanField(default=True)


class AuthorizePurgeSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    rejection_reason = serializers.CharField(required=False, allow_blank=True)
