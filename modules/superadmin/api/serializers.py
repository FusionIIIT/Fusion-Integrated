"""DRF serializers for Super Admin."""
from rest_framework import serializers

from modules.superadmin.models import AuditEntry, RoleAssignment, UserAccount


class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = [
            "id",
            "user_id",
            "institute_id",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "status",
            "deactivated_at",
            "archived_at",
            "reversible_until",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "deactivated_at",
            "archived_at",
            "reversible_until",
            "created_at",
        ]


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user_id",
            "role_code",
            "role_name",
            "scope",
            "is_singular",
            "start_date",
            "end_date",
            "status",
        ]
        read_only_fields = ["id", "status"]


class AuditEntrySerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditEntry
        fields = ["id", "timestamp", "actor_username", "action", "target_id", "result", "reason"]
        read_only_fields = fields
