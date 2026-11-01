from rest_framework import serializers
from modules.super_admin.models import UserAccount, RoleAssignment, SystemAuditLog

class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ['id', 'institute_id', 'username', 'email', 'user_type', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = ['id', 'user', 'role_name', 'assigned_by', 'start_date', 'end_date', 'reason', 'status', 'created_at']
        read_only_fields = ['id', 'created_at']

class SystemAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAuditLog
        fields = ['id', 'actor_username', 'action', 'target', 'details', 'timestamp']
        read_only_fields = ['id', 'timestamp']

class UserStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=['active', 'deactivated', 'archived'])
    reason = serializers.CharField(required=False, allow_blank=True)