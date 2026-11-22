"""Serializers for RoleAssignment models and actions."""
from __future__ import annotations

from rest_framework import serializers

from modules.system_admin.models.role_assignment import RoleAssignment


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = (
            "id",
            "role_code",
            "role_name",
            "user_id",
            "status",
            "is_singular",
            "start_date",
            "end_date",
            "scope",
            "reason",
            "assigned_by",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class AssignRoleSerializer(serializers.Serializer):
    role_code = serializers.CharField(max_length=64, required=False, default="")
    role_name = serializers.CharField(max_length=120, required=False, default="")
    user_id = serializers.IntegerField(required=False)
    user = serializers.IntegerField(required=False)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    scope = serializers.CharField(max_length=80, required=False, default="")
    reason = serializers.CharField(max_length=500, required=False, default="Role assignment")
    assigned_by = serializers.CharField(required=False, allow_null=True, default="1")
    is_singular = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs):
        if not attrs.get("role_code") and attrs.get("role_name"):
            attrs["role_code"] = attrs["role_name"]
        if not attrs.get("role_code"):
            raise serializers.ValidationError("role_code or role_name is required.")
        if attrs.get("user_id") is None and attrs.get("user") is not None:
            attrs["user_id"] = attrs["user"]
        if attrs.get("user_id") is None:
            raise serializers.ValidationError("user_id or user is required.")
        return attrs


class ReassignRoleSerializer(serializers.Serializer):
    new_user_id = serializers.IntegerField()
    effective_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)
    transfer_pending_tasks = serializers.BooleanField(required=False, default=True)


class RevokeRoleSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500, required=False, default="Role revoked")
    is_emergency = serializers.BooleanField(required=False, default=False)


class ExtendRoleSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=500)


class RoleDirectoryEntrySerializer(serializers.Serializer):
    role_code = serializers.CharField()
    role_name = serializers.CharField()
    is_singular = serializers.BooleanField()
    category = serializers.CharField()
    active_holders_count = serializers.IntegerField()
    is_vacant = serializers.BooleanField()
    holders = serializers.ListField(child=serializers.DictField())
