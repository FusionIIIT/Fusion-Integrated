"""Serializers for audit logs and security logs."""
from __future__ import annotations

from rest_framework import serializers

from modules.system_admin.models.audit import FailedLoginLog, SystemAuditLog


class SystemAuditLogSerializer(serializers.ModelSerializer):
    actor_username = serializers.SerializerMethodField()
    target = serializers.SerializerMethodField()
    details = serializers.SerializerMethodField()

    class Meta:
        model = SystemAuditLog
        fields = (
            "id",
            "actor_id",
            "actor_username",
            "action",
            "target",
            "target_id",
            "ip_address",
            "result",
            "details",
            "context",
            "timestamp",
        )
        read_only_fields = fields

    def get_actor_username(self, obj) -> str:
        return f"user_{obj.actor_id}"

    def get_target(self, obj) -> str:
        return obj.target_id

    def get_details(self, obj) -> dict:
        return obj.context


class FailedLoginLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = FailedLoginLog
        fields = (
            "id",
            "username",
            "ip_address",
            "attempted_at",
            "reason",
        )
        read_only_fields = fields
