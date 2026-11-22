"""Serializers for Archival and Purge models and workflows."""
from __future__ import annotations

from rest_framework import serializers

from modules.system_admin.models.archive import (
    ArchivedUserRecord,
    HistoricalDatasetArchive,
    PermanentPurgeRequest,
)


class ArchivedUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedUserRecord
        fields = (
            "user_id",
            "institute_id",
            "username",
            "email",
            "user_type",
            "reason",
            "retention_option",
            "archived_by",
            "archived_at",
            "reversible_until",
            "is_permanent",
            "snapshot",
            "created_at",
        )
        read_only_fields = fields


class ArchiveUserActionSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500)
    retention_option = serializers.CharField(default="standard_7yr")
    reversible_days = serializers.IntegerField(default=90)


class RestoreUserActionSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class HistoricalDatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalDatasetArchive
        fields = (
            "id",
            "category",
            "description",
            "date_range_start",
            "date_range_end",
            "record_count",
            "backup_reference",
            "archived_by",
            "is_restored",
            "created_at",
        )
        read_only_fields = ("id", "archived_by", "is_restored", "created_at")


class PurgeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PermanentPurgeRequest
        fields = (
            "id",
            "dataset_identifier",
            "requested_by",
            "requested_at",
            "retention_verified",
            "reason",
            "status",
            "it_head_user_id",
            "it_head_decided_at",
            "it_head_remarks",
            "created_at",
        )
        read_only_fields = (
            "id",
            "requested_by",
            "requested_at",
            "retention_verified",
            "status",
            "it_head_user_id",
            "it_head_decided_at",
            "created_at",
        )


class CreatePurgeRequestSerializer(serializers.Serializer):
    dataset_identifier = serializers.CharField(max_length=128)
    retention_years = serializers.FloatField()
    reason = serializers.CharField(max_length=500)


class PurgeAuthorizeSerializer(serializers.Serializer):
    approve = serializers.BooleanField()
    remarks = serializers.CharField(max_length=500, required=False, default="")
