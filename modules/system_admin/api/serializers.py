"""Serializers for modules.system_admin.

Explicit field declarations and allow-lists prevent unintended attribute mutation.
Traceability: CFR-SA-001..023, BR-SA-001, BR-SA-003, BR-SA-007, BR-SA-009, BR-SA-030.
"""
from __future__ import annotations

import datetime
from typing import Any, Dict

from django.utils import timezone
from rest_framework import serializers

from modules.system_admin.domain import validators
from modules.system_admin.domain.dataclasses import UserCreationSpec
from modules.system_admin.domain.exceptions import IdentityValidationError
from modules.system_admin.models import (
    ArchivedUserRecord,
    BasicUser,
    HistoricalDataArchive,
    PurgeRequest,
    RoleAssignment,
    RoleDefinition,
    SuperAdminAuditLog,
    UserProfile,
)


# ==============================================================================
# INPUT / REQUEST SERIALIZERS
# ==============================================================================


class BasicUserCreateSerializer(serializers.Serializer):
    """Payload for creating a single user (UC-SA-001)."""

    user_kind = serializers.ChoiceField(
        choices=[("student", "Student"), ("faculty", "Faculty"), ("staff", "Staff")]
    )
    name = serializers.CharField(max_length=255)
    institute_email = serializers.EmailField()
    institute_id = serializers.CharField(max_length=50)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    department = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    programme = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    discipline = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    batch_year = serializers.IntegerField(required=False, allow_null=True, default=None)
    employee_id = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    date_of_joining = serializers.DateField(required=False, allow_null=True, default=None)
    expected_completion_date = serializers.DateField(required=False, allow_null=True, default=None)
    initial_password = serializers.CharField(max_length=128, required=False, allow_blank=True, default="")

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        spec = UserCreationSpec(
            user_kind=attrs["user_kind"],
            name=attrs["name"],
            institute_email=attrs["institute_email"],
            institute_id=attrs["institute_id"],
            contact_number=attrs.get("contact_number", ""),
            department=attrs.get("department", ""),
            programme=attrs.get("programme", ""),
            discipline=attrs.get("discipline", ""),
            batch_year=attrs.get("batch_year"),
            employee_id=attrs.get("employee_id", ""),
            date_of_joining=attrs.get("date_of_joining"),
            expected_completion_date=attrs.get("expected_completion_date"),
        )
        try:
            validators.validate_user_type_required_data(spec)
        except IdentityValidationError as exc:
            raise serializers.ValidationError(exc.message) from exc

        return attrs


class BasicUserProfileUpdateSerializer(serializers.Serializer):
    """Payload for updating user profile fields. Prohibits institute_id modification (BR-SA-001)."""

    display_name = serializers.CharField(required=False, max_length=255)
    contact_number = serializers.CharField(required=False, max_length=20, allow_blank=True)
    department = serializers.CharField(required=False, max_length=100, allow_blank=True)
    programme = serializers.CharField(required=False, max_length=100, allow_blank=True)
    discipline = serializers.CharField(required=False, max_length=100, allow_blank=True)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    employee_id = serializers.CharField(required=False, max_length=50, allow_blank=True)
    email = serializers.EmailField(required=False)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        if "institute_id" in self.initial_data:
            raise serializers.ValidationError(
                {"institute_id": "Institute ID is immutable once assigned (BR-SA-001)."}
            )
        return attrs


class BulkUserCSVUploadSerializer(serializers.Serializer):
    """Handles CSV file upload for batch user onboarding (UC-SA-002, BR-SA-030)."""

    csv_file = serializers.FileField()

    def validate_csv_file(self, value: Any) -> Any:
        if not value.name.lower().endswith(".csv"):
            raise serializers.ValidationError("Uploaded file must be a .csv file.")
        if value.size > 5 * 1024 * 1024:
            raise serializers.ValidationError("File size exceeds 5MB limit.")
        return value


class BulkStatusUpdateSerializer(serializers.Serializer):
    """Payload for bulk deactivation or reactivation (UC-SA-003, BR-SA-030)."""

    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=1000,
        help_text="Capped at 1000 records per operation (BR-SA-030).",
    )
    action = serializers.ChoiceField(choices=["deactivate", "reactivate"])
    reason = serializers.CharField(max_length=255)


class UserActionReasonSerializer(serializers.Serializer):
    """Generic payload for operations requiring a justification reason."""

    reason = serializers.CharField(max_length=255)


class RoleAssignmentCreateSerializer(serializers.Serializer):
    """Payload for assigning a role to a user (UC-SA-006)."""

    role_code = serializers.CharField(max_length=100)
    target_user_id = serializers.IntegerField()
    scope = serializers.CharField(max_length=100, default="institute")
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True, default=None)
    reason = serializers.CharField(max_length=255, required=False, allow_blank=True, default="")

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        start = attrs.get("start_date")
        end = attrs.get("end_date")
        if start and end and end <= start:
            raise serializers.ValidationError(
                {"end_date": "End date must be strictly after start date."}
            )
        return attrs


class RoleReassignmentSerializer(serializers.Serializer):
    """Payload for reassigning a singular or key role to a successor (UC-SA-007, BR-SA-014)."""

    new_holder_id = serializers.IntegerField()
    effective_date = serializers.DateField()
    handover_tasks = serializers.BooleanField(default=True)
    audit_access_days = serializers.IntegerField(default=90)
    reason = serializers.CharField(max_length=255)

    def validate_effective_date(self, value: datetime.date) -> datetime.date:
        if value < timezone.now().date():
            raise serializers.ValidationError("Effective date cannot be in the past.")
        return value


class RoleRevocationSerializer(serializers.Serializer):
    """Payload for revoking a role (UC-SA-008, BR-SA-011)."""

    is_emergency = serializers.BooleanField(default=False)
    notice_date = serializers.DateField(required=False)
    effective_date = serializers.DateField()
    reason = serializers.CharField(max_length=255)
    pending_tasks_disposition = serializers.ChoiceField(
        choices=["transfer", "close"], default="transfer"
    )
    new_task_holder_id = serializers.IntegerField(required=False, allow_null=True, default=None)

    def validate(self, attrs: Dict[str, Any]) -> Dict[str, Any]:
        notice_date = attrs.get("notice_date", timezone.now().date())
        effective_date = attrs["effective_date"]
        is_emergency = attrs.get("is_emergency", False)

        try:
            validators.validate_revocation_notice(
                is_emergency=is_emergency,
                notice_date=notice_date,
                effective_date=effective_date,
            )
        except Exception as exc:
            raise serializers.ValidationError(str(exc)) from exc

        return attrs


class RoleExtensionSerializer(serializers.Serializer):
    """Payload for extending a role validity period (UC-SA-010)."""

    new_end_date = serializers.DateField()
    reason = serializers.CharField(max_length=255)


class ActiveRoleSwitchSerializer(serializers.Serializer):
    """Payload for switching active role in a multi-role context (UC-SA-011)."""

    target_role_code = serializers.CharField(max_length=100)


class PurgeRequestCreateSerializer(serializers.Serializer):
    """Payload for requesting permanent account purge (UC-SA-014, BR-SA-022)."""

    archive_id = serializers.IntegerField()
    reason = serializers.CharField(max_length=500)


class PurgeAuthorizationDecisionSerializer(serializers.Serializer):
    """Payload for IT Head dual-authorization decision (CW-SA-01)."""

    approved = serializers.BooleanField()
    comments = serializers.CharField(required=False, allow_blank=True, default="")


class SystemParameterUpdateSerializer(serializers.Serializer):
    """Payload for updating permitted system parameters (UC-SA-018, BR-SA-035)."""

    value = serializers.CharField()


class HistoricalArchiveCreateSerializer(serializers.Serializer):
    """Payload for triggering historical data archival (UC-SA-013, BR-SA-019)."""

    category = serializers.CharField(max_length=64)
    date_range_start = serializers.DateField()
    date_range_end = serializers.DateField()
    record_count = serializers.IntegerField(default=0)
    backup_file_path = serializers.CharField(max_length=255, default="")
    backup_checksum = serializers.CharField(max_length=64, default="")
    retention_years = serializers.IntegerField(default=5)


# ==============================================================================
# RESPONSE / DETAIL SERIALIZERS
# ==============================================================================


class UserProfileDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = (
            "display_name",
            "contact_number",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "employee_id",
            "extra_attributes",
        )


class BasicUserDetailSerializer(serializers.ModelSerializer):
    profile = UserProfileDetailSerializer(read_only=True)

    class Meta:
        model = BasicUser
        fields = (
            "id",
            "username",
            "institute_id",
            "email",
            "kind",
            "is_active",
            "status",
            "deactivated_at",
            "date_of_joining",
            "expected_completion_date",
            "profile",
            "created_at",
            "updated_at",
        )


class RoleDefinitionDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleDefinition
        fields = (
            "code",
            "label",
            "category",
            "allowed_kinds",
            "is_singular",
            "is_time_bound",
            "default_lead_time_days",
            "is_active",
            "description",
            "created_at",
        )


class RoleAssignmentDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoleAssignment
        fields = (
            "id",
            "user_id",
            "role_id",
            "scope",
            "start_date",
            "end_date",
            "state",
            "assigned_by",
            "reason",
            "activated_at",
            "expired_at",
            "revoked_at",
            "created_at",
        )


class ArchivedUserDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedUserRecord
        fields = (
            "basic_user_id",
            "institute_id",
            "username",
            "email",
            "kind",
            "archived_at",
            "reversible_until",
            "status",
            "archival_reason",
            "authorized_by",
            "restored_at",
            "user_data_snapshot",
        )


class HistoricalDataArchiveDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalDataArchive
        fields = (
            "id",
            "dataset_category",
            "date_range_start",
            "date_range_end",
            "record_count",
            "backup_file_path",
            "backup_checksum",
            "archived_at",
            "archived_by",
            "retention_expires_at",
            "is_restored",
            "is_purged",
        )


class PurgeRequestDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = PurgeRequest
        fields = (
            "id",
            "archive_id",
            "status",
            "requested_by",
            "requested_at",
            "request_reason",
            "it_head_id",
            "it_head_decision_at",
            "it_head_comments",
            "purged_at",
        )


class SuperAdminAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SuperAdminAuditLog
        fields = (
            "id",
            "timestamp",
            "actor_id",
            "actor_username",
            "action",
            "target_user_id",
            "target_role_code",
            "ip_address",
            "user_agent",
            "result",
            "reason",
            "context_metadata",
        )


class DashboardMetricsSerializer(serializers.Serializer):
    users = serializers.DictField()
    roles = serializers.DictField()
    archival = serializers.DictField()
    security = serializers.DictField()
    timestamp = serializers.DateTimeField()
