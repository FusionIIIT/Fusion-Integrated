"""Serializers for DepartmentRoleAssignment."""
from rest_framework import serializers

from modules.department.models import DepartmentRoleAssignment


class RoleAssignmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = DepartmentRoleAssignment
        fields = [
            'id',
            'department',
            'role',
            'user_id',
            'valid_from',
            'valid_to',
            'assigned_by_user_id',
            'transition_applied_at',
        ]

class RoleAssignmentCreateSerializer(serializers.Serializer):
    department = serializers.IntegerField()
    role = serializers.ChoiceField(choices=['hod', 'dept_admin'])
    user_id = serializers.IntegerField()
    valid_from = serializers.DateTimeField()
    valid_to = serializers.DateTimeField()
