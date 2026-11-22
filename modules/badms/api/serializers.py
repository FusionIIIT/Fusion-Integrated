from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.conf import settings
from rest_framework import serializers

from modules.badms.models import (
    ArchivalRequest,
    BackupRun,
    BackupSchedule,
    RestoreRequest,
    SecurityPolicyVersion,
    StorageExtensionRequest,
)


class BackupRunSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupRun
        fields = (
            "id", "dataset_key", "trigger", "status", "started_at",
            "finished_at", "checksum_sha256", "size_bytes", "created_at",
        )
        read_only_fields = fields


class BackupScheduleSerializer(serializers.ModelSerializer):
    class Meta:
        model = BackupSchedule
        fields = (
            "id", "scope", "dataset_key", "cron_expression", "timezone",
            "classification_filters", "enabled", "created_at", "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate_cron_expression(self, value):
        fields = value.split()
        if len(fields) != 5:
            raise serializers.ValidationError(
                "Use a five-field cron expression (minute hour day month weekday).")
        try:
            from celery.schedules import crontab

            crontab(minute=fields[0], hour=fields[1], day_of_month=fields[2],
                    month_of_year=fields[3], day_of_week=fields[4])
        except (ValueError, KeyError) as exc:
            raise serializers.ValidationError("Invalid cron expression.") from exc
        return value

    def validate_timezone(self, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise serializers.ValidationError("Unknown timezone.") from exc
        return value

    def validate_dataset_key(self, value):
        if value not in settings.BADMS_DATASETS:
            raise serializers.ValidationError(
                "Choose a configured backup dataset.")
        return value

    def validate_classification_filters(self, value):
        if value:
            raise serializers.ValidationError(
                "Classification filters are unavailable until the dataset "
                "adapter is configured.")
        return value

    def validate(self, attrs):
        actor = self.context["request"].principal
        attrs["changed_by_user_id"] = actor.user_id
        if (attrs.get("scope") == BackupSchedule.Scope.GLOBAL
                and not actor.has_permission("badms.schedule.update")):
            raise serializers.ValidationError(
                "Only an authorized global scheduler may create global schedules.")
        return attrs


class ArchivalRequestSerializer(serializers.ModelSerializer):
    attachment = serializers.FileField(write_only=True, required=True)

    class Meta:
        model = ArchivalRequest
        fields = (
            "id", "file_name", "data_date", "owners", "file_type", "reason",
            "department_code", "special_operation",
            "initial_classification", "classification", "status", "attachment",
            "decision_reason", "created_at", "updated_at",
        )
        read_only_fields = (
            "id", "classification", "status", "decision_reason",
            "department_code", "special_operation", "created_at", "updated_at",
        )

    def validate_attachment(self, value):
        if value.size > settings.BADMS_ATTACHMENT_MAX_BYTES:
            raise serializers.ValidationError(
                "The attachment exceeds the configured size limit.")
        if Path(value.name).suffix.casefold() not in {
            ".csv", ".doc", ".docx", ".pdf", ".txt", ".xls", ".xlsx",
        }:
            raise serializers.ValidationError("This attachment type is not allowed.")
        return value

    def validate_file_name(self, value):
        if Path(value).name != value or any(char in value for char in "\r\n"):
            raise serializers.ValidationError("Use a plain file name, not a path.")
        return value


class ArchivalDecisionSerializer(serializers.Serializer):
    approved = serializers.BooleanField()
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)


class ClassificationSerializer(serializers.Serializer):
    classification = serializers.ChoiceField(
        choices=ArchivalRequest.Classification.choices,
    )


class RestoreRequestSerializer(serializers.ModelSerializer):
    archive_classification = serializers.CharField(
        source="archive.classification", read_only=True,
    )
    file_name = serializers.CharField(source="archive.file_name", read_only=True)

    class Meta:
        model = RestoreRequest
        fields = (
            "id", "archive", "archive_classification", "file_name", "reason",
            "status", "decision_at", "created_at",
        )
        read_only_fields = ("id", "status", "decision_at", "created_at")


class StorageExtensionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StorageExtensionRequest
        fields = (
            "id", "current_usage_bytes", "quota_bytes", "requested_bytes",
            "justification", "status", "decision_reason", "created_at",
        )
        read_only_fields = (
            "id", "current_usage_bytes", "quota_bytes", "status",
            "decision_reason", "created_at",
        )

    def validate_requested_bytes(self, value):
        if value <= 0:
            raise serializers.ValidationError("Requested capacity must be positive.")
        return value


class SecurityPolicySerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityPolicyVersion
        fields = (
            "id", "classification", "effective_from", "retention_days",
            "encryption_required", "created_by_user_id", "created_at",
        )
        read_only_fields = ("id", "created_by_user_id", "created_at")

    def validate(self, attrs):
        actor = self.context["request"].principal
        attrs["created_by_user_id"] = actor.user_id
        if (attrs.get("classification") == ArchivalRequest.Classification.SENSITIVE
                and not attrs.get("encryption_required", False)):
            raise serializers.ValidationError({
                "encryption_required": "Sensitive data must require encryption.",
            })
        return attrs
