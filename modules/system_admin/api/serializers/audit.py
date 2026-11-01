"""Audit and monitoring serializers for System Admin module."""
from rest_framework import serializers

from modules.system_admin.models import AuditLog


class AuditLogReadSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLog
        fields = [
            "id",
            "timestamp",
            "actor_user_id",
            "actor_username",
            "action",
            "target_type",
            "target_id",
            "ip_address",
            "result",
            "reason",
            "details",
        ]
        read_only_fields = fields


class SuperAdminLoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=64)
    password = serializers.CharField(max_length=128)
    two_factor_code = serializers.CharField(max_length=16)


class SuperAdminLogoutSerializer(serializers.Serializer):
    session_key = serializers.CharField(max_length=128)
