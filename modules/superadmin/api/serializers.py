"""Serializers for Super Admin endpoints."""

from rest_framework import serializers

from modules.superadmin.models import (
    AuditLogRecord,
    HistoricalArchiveRecord,
    PurgeRequestRecord,
    RoleAssignmentRecord,
    RoleHandoverRecord,
    SystemParameterPolicy,
    UserAccountRecord,
)


class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccountRecord
        fields = [
            "id",
            "user_id",
            "institute_id",
            "email",
            "user_type",
            "activation_status",
            "deactivation_date",
            "archival_date",
            "reversibility_expires_at",
            "department",
            "program",
            "batch",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "activation_status",
            "deactivation_date",
            "archival_date",
            "reversibility_expires_at",
            "created_at",
            "updated_at",
        ]


class CreateUserAccountSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    institute_id = serializers.CharField(max_length=64)
    email = serializers.EmailField()
    user_type = serializers.ChoiceField(choices=["STUDENT", "FACULTY", "STAFF"])
    department = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")
    program = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    batch = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")


class UpdateUserProfileSerializer(serializers.Serializer):
    department = serializers.CharField(max_length=128, required=False)
    program = serializers.CharField(max_length=64, required=False)
    batch = serializers.CharField(max_length=32, required=False)


class StatusReasonSerializer(serializers.Serializer):
    reason = serializers.CharField(max_length=500)


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignmentRecord
        fields = [
            "id",
            "user_id",
            "role_name",
            "scope_type",
            "scope_id",
            "valid_from",
            "valid_to",
            "status",
            "is_singular",
            "assigned_by_user_id",
            "assignment_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "assigned_by_user_id",
            "created_at",
            "updated_at",
        ]


class AssignRoleSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    role_name = serializers.CharField(max_length=128)
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField(required=False, allow_null=True)
    scope_type = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    scope_id = serializers.CharField(max_length=64, required=False, allow_blank=True, default="")
    is_singular = serializers.BooleanField(required=False, default=False)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class ExtendRoleSerializer(serializers.Serializer):
    new_valid_to = serializers.DateTimeField()
    reason = serializers.CharField(max_length=500)


class ReassignRoleSerializer(serializers.Serializer):
    successor_user_id = serializers.IntegerField(min_value=1)
    effective_date = serializers.DateTimeField()
    handover_summary = serializers.CharField(
        max_length=1000, required=False, allow_blank=True, default=""
    )


class RoleHandoverSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleHandoverRecord
        fields = [
            "id",
            "role_assignment",
            "from_user_id",
            "to_user_id",
            "effective_date",
            "pending_work_summary",
            "audit_access_granted",
            "created_at",
        ]
        read_only_fields = fields


class HistoricalArchiveSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalArchiveRecord
        fields = [
            "id",
            "entity_type",
            "record_identifier",
            "payload",
            "backup_reference",
            "retention_period_days",
            "purge_eligible_at",
            "status",
            "archived_by_user_id",
            "created_at",
        ]
        read_only_fields = fields


class PurgeRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurgeRequestRecord
        fields = [
            "id",
            "archive_record",
            "requested_by_user_id",
            "request_reason",
            "status",
            "authorized_by_user_id",
            "authorized_at",
            "rejection_reason",
            "created_at",
        ]
        read_only_fields = [
            "id",
            "status",
            "authorized_by_user_id",
            "authorized_at",
            "rejection_reason",
            "created_at",
        ]


class AuthorizePurgeSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["APPROVE", "REJECT"])
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True, default="")


class RequestPurgeSerializer(serializers.Serializer):
    archive_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=500)


class BulkUserCreateSerializer(serializers.Serializer):
    csv_data = serializers.CharField(required=False, allow_blank=True)
    file = serializers.FileField(required=False)


class BulkOperationResultSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    success_count = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.DictField())


class DashboardMetricsSerializer(serializers.Serializer):
    total_users = serializers.IntegerField()
    active_users = serializers.IntegerField()
    deactivated_users = serializers.IntegerField()
    archived_reversible_users = serializers.IntegerField()
    archived_permanent_users = serializers.IntegerField()


class AuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = AuditLogRecord
        fields = [
            "id",
            "event_type",
            "actor_user_id",
            "target_entity",
            "target_id",
            "ip_address",
            "action_details",
            "is_immutable",
            "created_at",
        ]
        read_only_fields = fields


class SystemParameterSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemParameterPolicy
        fields = [
            "id",
            "parameter_key",
            "parameter_value",
            "version",
            "effective_from",
            "effective_to",
            "is_active",
            "updated_by_user_id",
            "created_at",
        ]
        read_only_fields = fields


class UpdateSystemParameterSerializer(serializers.Serializer):
    parameter_key = serializers.CharField(max_length=128)
    parameter_value = serializers.JSONField()
    effective_from = serializers.DateTimeField(required=False, allow_null=True)


class BulkStatusUpdateSerializer(serializers.Serializer):
    user_ids = serializers.ListField(child=serializers.IntegerField(min_value=1), min_length=1)
    target_status = serializers.ChoiceField(choices=["ACTIVE", "DEACTIVATED"])
    reason = serializers.CharField(max_length=500)
