"""Role serializers for System Admin module."""
from rest_framework import serializers

from modules.system_admin.domain import (
    validate_role_dates,
)
from modules.system_admin.models import RoleAssignment, RoleDefinition


class RoleDefinitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleDefinition
        fields = [
            "id",
            "code",
            "name",
            "description",
            "module_association",
            "department_association",
            "allowed_user_types",
            "is_singular",
            "default_validity_days",
            "permissions",
            "conflict_role_codes",
            "is_system_role",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class RoleAssignmentReadSerializer(serializers.ModelSerializer):
    role_code = serializers.CharField(source="role.code", read_only=True)
    role_name = serializers.CharField(source="role.name", read_only=True)
    module_association = serializers.CharField(source="role.module_association", read_only=True)

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user_id",
            "role_code",
            "role_name",
            "module_association",
            "start_date",
            "end_date",
            "scope_type",
            "scope_id",
            "reason",
            "status",
            "assigned_by_user_id",
            "assigned_at",
            "effective_revoked_at",
            "revocation_reason",
            "pending_task_disposition",
            "previous_assignment_id",
            "previous_holder_audit_until",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    role_code = serializers.CharField(max_length=64)
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    scope_type = serializers.CharField(max_length=32, default="institute")
    scope_id = serializers.CharField(max_length=64, default="", allow_blank=True)
    reason = serializers.CharField(required=False, allow_blank=True)


class ReassignRoleSerializer(serializers.Serializer):
    new_user_id = serializers.IntegerField()
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=True)
    audit_access_days = serializers.IntegerField(default=30)


class RevokeRoleSerializer(serializers.Serializer):
    effective_date = serializers.DateField()
    reason = serializers.CharField(required=True)
    pending_task_disposition = serializers.ChoiceField(choices=["transfer", "close"], default="transfer")
    is_emergency = serializers.BooleanField(default=False)


class ExtendRoleSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    reason = serializers.CharField(required=True)


class SwitchActiveRoleSerializer(serializers.Serializer):
    role_code = serializers.CharField(max_length=64)
