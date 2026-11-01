"""User serializers for System Admin module."""
from rest_framework import serializers

from modules.system_admin.domain import (
    validate_bulk_operation_limit,
    validate_institute_email,
    validate_user_type_required_data,
)
from modules.system_admin.models import BasicUser, BulkOperationLog


class BasicUserReadSerializer(serializers.ModelSerializer):
    display_name = serializers.SerializerMethodField()

    class Meta:
        model = BasicUser
        fields = [
            "user_id",
            "institute_id",
            "user_type",
            "email",
            "first_name",
            "last_name",
            "display_name",
            "contact_number",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "employee_id",
            "date_of_joining",
            "expected_completion_date",
            "status",
            "dashboard_access_enabled",
            "deactivated_at",
            "deactivation_reason",
            "archived_at",
            "archival_reason",
            "reversible_until",
            "is_permanently_archived",
            "has_pending_transactions",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_display_name(self, obj: BasicUser) -> str:
        return f"{obj.first_name} {obj.last_name}"


class BasicUserCreateSerializer(serializers.Serializer):
    institute_id = serializers.CharField(max_length=32)
    user_type = serializers.ChoiceField(choices=["student", "faculty", "staff"])
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=64)
    last_name = serializers.CharField(max_length=64)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=80, required=False, allow_blank=True)
    programme = serializers.CharField(max_length=40, required=False, allow_blank=True)
    discipline = serializers.CharField(max_length=40, required=False, allow_blank=True)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    employee_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    expected_completion_date = serializers.DateField(required=False, allow_null=True)

    def validate(self, attrs):
        validate_institute_email(attrs["email"])
        validate_user_type_required_data(attrs["user_type"], attrs)
        return attrs


class BasicUserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    first_name = serializers.CharField(max_length=64, required=False)
    last_name = serializers.CharField(max_length=64, required=False)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=80, required=False, allow_blank=True)
    programme = serializers.CharField(max_length=40, required=False, allow_blank=True)
    discipline = serializers.CharField(max_length=40, required=False, allow_blank=True)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    employee_id = serializers.CharField(max_length=32, required=False, allow_blank=True)
    date_of_joining = serializers.DateField(required=False, allow_null=True)
    expected_completion_date = serializers.DateField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_blank=True)

    def validate_institute_id(self, value):
        # BR-SA-001: Institute ID is immutable once created
        raise serializers.ValidationError("Institute ID is immutable and cannot be modified.")


class UserStatusActionSerializer(serializers.Serializer):
    reason = serializers.CharField(required=True)


class BulkUserCreateSerializer(serializers.Serializer):
    records = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=False,
    )

    def validate_records(self, value):
        validate_bulk_operation_limit(len(value), limit=1000)
        return value


class BulkStatusUpdateSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        allow_empty=False,
    )
    target_status = serializers.ChoiceField(choices=["active", "deactivated"])
    reason = serializers.CharField(required=True)

    def validate_user_ids(self, value):
        validate_bulk_operation_limit(len(value), limit=1000)
        return value


class BulkOperationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = BulkOperationLog
        fields = "__all__"
