"""Serializers for UserAccount models and workflows."""
from __future__ import annotations

from rest_framework import serializers

from modules.system_admin.models.user_account import UserAccount


class UserAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = (
            "user_id",
            "institute_id",
            "username",
            "email",
            "user_type",
            "name",
            "contact_number",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "status",
            "deactivated_at",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields


class CreateUserSerializer(serializers.Serializer):
    institute_id = serializers.CharField(max_length=32)
    username = serializers.CharField(max_length=64)
    email = serializers.EmailField()
    user_type = serializers.ChoiceField(choices=["student", "faculty", "staff"])
    name = serializers.CharField(max_length=150, required=False, default="")
    contact_number = serializers.CharField(max_length=32, required=False, default="")
    department = serializers.CharField(max_length=80, required=False, default="")
    programme = serializers.CharField(max_length=40, required=False, default="")
    discipline = serializers.CharField(max_length=40, required=False, default="")
    batch_year = serializers.IntegerField(required=False, allow_null=True, default=None)
    user_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class UpdateUserSerializer(serializers.Serializer):
    name = serializers.CharField(max_length=150, required=False)
    email = serializers.EmailField(required=False)
    contact_number = serializers.CharField(max_length=32, required=False)
    department = serializers.CharField(max_length=80, required=False)
    programme = serializers.CharField(max_length=40, required=False)
    discipline = serializers.CharField(max_length=40, required=False)
    batch_year = serializers.IntegerField(required=False, allow_null=True)


class UserStatusSerializer(serializers.Serializer):
    action = serializers.CharField(required=False, default="")
    status = serializers.CharField(required=False, default="")
    reason = serializers.CharField(max_length=500, required=False, default="Status update")
    institute_id = serializers.CharField(required=False, allow_null=True)

    def validate(self, attrs):
        if not attrs.get("action") and attrs.get("status"):
            attrs["action"] = attrs["status"]
        if not attrs.get("action"):
            attrs["action"] = "deactivate"
        return attrs


class BulkCreateUsersSerializer(serializers.Serializer):
    users = CreateUserSerializer(many=True)


class BulkCreateResultSerializer(serializers.Serializer):
    created_count = serializers.IntegerField()
    error_count = serializers.IntegerField()
    errors = serializers.ListField(child=serializers.DictField())


class DashboardMetricsSerializer(serializers.Serializer):
    users = serializers.DictField()
    roles = serializers.DictField()
    security = serializers.DictField()
    archives = serializers.DictField()
    system_health = serializers.DictField()
