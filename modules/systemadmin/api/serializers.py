"""DRF Serializers for System Admin Module."""
from rest_framework import serializers
from modules.systemadmin.models.user_mgmt import BasicUserProfile, UserStatusHistory
from modules.systemadmin.models.role_mgmt import RoleDefinition, RoleConflict, RoleAssignment, RoleAssignmentHistory
from modules.systemadmin.models.archival import ArchivedUser, ArchivedHistoricalData, PermanentPurgeRequest
from modules.systemadmin.models.audit import SystemAdminAuditLog, SessionLog, SecurityAlert, AdminNotification
from modules.systemadmin.models.config import SystemAdminConfig


class UserStatusHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = UserStatusHistory
        fields = ["id", "from_status", "to_status", "changed_at", "actor_username", "reason"]


class BasicUserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = BasicUserProfile
        fields = [
            "id",
            "internal_user_id",
            "institute_id",
            "institute_email",
            "full_name",
            "user_type",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "employee_id",
            "date_of_joining",
            "expected_completion_date",
            "contact_number",
            "status",
            "deactivated_at",
            "deactivation_reason",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "internal_user_id",
            "institute_id",
            "institute_email",
            "status",
            "created_at",
            "updated_at",
        ]


class BasicUserProfileDetailSerializer(serializers.ModelSerializer):
    status_history = UserStatusHistorySerializer(many=True, read_only=True)
    active_roles = serializers.SerializerMethodField()

    class Meta:
        model = BasicUserProfile
        fields = [
            "id",
            "internal_user_id",
            "institute_id",
            "institute_email",
            "full_name",
            "user_type",
            "department",
            "programme",
            "discipline",
            "batch_year",
            "employee_id",
            "date_of_joining",
            "expected_completion_date",
            "contact_number",
            "status",
            "deactivated_at",
            "deactivation_reason",
            "status_history",
            "active_roles",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "internal_user_id",
            "institute_id",
            "institute_email",
            "status",
            "created_at",
            "updated_at",
        ]

    def get_active_roles(self, obj):
        assignments = RoleAssignment.objects.filter(
            user=obj, status__in=["active", "extended"]
        ).select_related("role")
        return [
            {
                "id": a.id,
                "role_code": a.role.code,
                "role_name": a.role.name,
                "scope": a.scope,
                "start_date": a.start_date,
                "end_date": a.end_date,
                "status": a.status,
            }
            for a in assignments
        ]


class UserCreateSerializer(serializers.Serializer):
    institute_id = serializers.CharField(max_length=32)
    user_type = serializers.ChoiceField(choices=BasicUserProfile.USER_TYPE_CHOICES)
    full_name = serializers.CharField(max_length=150)
    institute_email = serializers.EmailField()
    date_of_joining = serializers.DateField()
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True, default="")
    department = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")
    programme = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    discipline = serializers.CharField(max_length=50, required=False, allow_blank=True, default="")
    batch_year = serializers.IntegerField(required=False, allow_null=True, default=None)
    employee_id = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    expected_completion_date = serializers.DateField(required=False, allow_null=True, default=None)


class UserUpdateSerializer(serializers.Serializer):
    full_name = serializers.CharField(max_length=150, required=False)
    contact_number = serializers.CharField(max_length=20, required=False, allow_blank=True)
    department = serializers.CharField(max_length=100, required=False)
    programme = serializers.CharField(max_length=50, required=False, allow_blank=True)
    discipline = serializers.CharField(max_length=50, required=False, allow_blank=True)
    batch_year = serializers.IntegerField(required=False, allow_null=True)
    expected_completion_date = serializers.DateField(required=False, allow_null=True)


class UserStatusChangeSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["deactivate", "reactivate"])
    reason = serializers.CharField(min_length=3)


class BulkUserCreateSerializer(serializers.Serializer):
    users = serializers.ListField(
        child=serializers.DictField(),
        max_length=1000,
        min_length=1,
    )


class BulkUserStatusSerializer(serializers.Serializer):
    user_ids = serializers.ListField(
        child=serializers.IntegerField(),
        max_length=1000,
        min_length=1,
    )
    action = serializers.ChoiceField(choices=["deactivate", "reactivate"])
    reason = serializers.CharField(min_length=3)


class RoleConflictSerializer(serializers.ModelSerializer):
    conflicting_role_code = serializers.CharField(source="role_b.code", read_only=True)
    conflicting_role_name = serializers.CharField(source="role_b.name", read_only=True)

    class Meta:
        model = RoleConflict
        fields = ["id", "conflicting_role_code", "conflicting_role_name", "reason"]


class RoleDefinitionSerializer(serializers.ModelSerializer):
    conflicts = serializers.SerializerMethodField()
    current_holder = serializers.SerializerMethodField()
    is_vacant = serializers.SerializerMethodField()

    class Meta:
        model = RoleDefinition
        fields = [
            "id",
            "code",
            "name",
            "description",
            "module_or_dept",
            "allowed_user_types",
            "is_singular",
            "is_time_bound",
            "default_validity_days",
            "permissions",
            "status",
            "conflicts",
            "current_holder",
            "is_vacant",
        ]

    def get_conflicts(self, obj):
        conflicts = RoleConflict.objects.filter(role_a=obj).select_related("role_b")
        return [
            {
                "id": c.id,
                "conflicting_role_code": c.role_b.code,
                "conflicting_role_name": c.role_b.name,
                "reason": c.reason,
            }
            for c in conflicts
        ]

    def get_current_holder(self, obj):
        if not obj.is_singular:
            return None
        active = (
            RoleAssignment.objects.filter(role=obj, status__in=["active", "extended"])
            .select_related("user")
            .first()
        )
        if active:
            return {
                "assignment_id": active.id,
                "user_id": active.user.id,
                "institute_id": active.user.institute_id,
                "full_name": active.user.full_name,
                "start_date": active.start_date,
                "end_date": active.end_date,
            }
        return None

    def get_is_vacant(self, obj):
        if obj.is_singular:
            return not RoleAssignment.objects.filter(role=obj, status__in=["active", "extended"]).exists()
        return False


class RoleAssignmentSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()
    role_details = serializers.SerializerMethodField()

    class Meta:
        model = RoleAssignment
        fields = [
            "id",
            "user",
            "user_details",
            "role",
            "role_details",
            "scope",
            "start_date",
            "end_date",
            "status",
            "assignment_reason",
            "assigned_by",
            "extended_at",
            "extension_reason",
            "revoked_at",
            "revocation_reason",
            "reassigned_to_user",
            "reassignment_effective_date",
            "previous_holder_audit_until",
            "created_at",
        ]

    def get_user_details(self, obj):
        return {
            "id": obj.user.id,
            "institute_id": obj.user.institute_id,
            "full_name": obj.user.full_name,
            "department": obj.user.department,
            "user_type": obj.user.user_type,
        }

    def get_role_details(self, obj):
        return {
            "id": obj.role.id,
            "code": obj.role.code,
            "name": obj.role.name,
            "is_singular": obj.role.is_singular,
            "module_or_dept": obj.role.module_or_dept,
        }


class RoleAssignmentCreateSerializer(serializers.Serializer):
    role_code = serializers.CharField(max_length=64)
    user_id = serializers.IntegerField()
    start_date = serializers.DateField()
    end_date = serializers.DateField(required=False, allow_null=True)
    scope = serializers.CharField(required=False, allow_blank=True, default="")
    reason = serializers.CharField(required=False, allow_blank=True, default="")


class RoleReassignSerializer(serializers.Serializer):
    new_user_id = serializers.IntegerField()
    effective_date = serializers.DateField()
    reason = serializers.CharField(min_length=3)
    pending_task_disposition = serializers.ChoiceField(
        choices=["transfer", "close"], default="transfer"
    )


class RoleRevokeSerializer(serializers.Serializer):
    reason = serializers.CharField(min_length=3)
    is_emergency = serializers.BooleanField(default=False)
    effective_date = serializers.DateField(required=False, allow_null=True)
    pending_task_disposition = serializers.ChoiceField(
        choices=["transfer", "close"], default="close"
    )


class RoleExtendSerializer(serializers.Serializer):
    new_end_date = serializers.DateField()
    extension_approval_ref = serializers.CharField(min_length=3)
    reason = serializers.CharField(min_length=3)


class ArchivedUserSerializer(serializers.ModelSerializer):
    user_details = serializers.SerializerMethodField()

    class Meta:
        model = ArchivedUser
        fields = [
            "id",
            "user",
            "user_details",
            "archival_date",
            "archived_at",
            "archived_by",
            "reason",
            "retention_option",
            "reversibility_deadline",
            "status",
            "restored_at",
            "restored_by",
            "restoration_authorization_ref",
        ]

    def get_user_details(self, obj):
        return {
            "id": obj.user.id,
            "institute_id": obj.user.institute_id,
            "full_name": obj.user.full_name,
            "institute_email": obj.user.institute_email,
            "user_type": obj.user.user_type,
            "department": obj.user.department,
        }


class ArchiveUserCreateSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    reason = serializers.CharField(min_length=3)
    retention_option = serializers.CharField(default="standard_institutional")


class RestoreUserSerializer(serializers.Serializer):
    restoration_authorization_ref = serializers.CharField(min_length=3)


class ArchivedHistoricalDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = ArchivedHistoricalData
        fields = "__all__"


class ArchiveHistoricalDataCreateSerializer(serializers.Serializer):
    category = serializers.CharField(max_length=64)
    date_range_start = serializers.DateField()
    date_range_end = serializers.DateField()
    record_count = serializers.IntegerField(min_value=0)
    storage_size_kb = serializers.IntegerField(min_value=0)
    backup_reference = serializers.CharField(max_length=120)
    retention_years = serializers.IntegerField(default=7, min_value=1)
    summary_metadata = serializers.DictField(required=False, default=dict)


class RestoreHistoricalDataSerializer(serializers.Serializer):
    approval_ref = serializers.CharField(min_length=3)


class PermanentPurgeRequestSerializer(serializers.ModelSerializer):
    target_summary = serializers.SerializerMethodField()

    class Meta:
        model = PermanentPurgeRequest
        fields = "__all__"

    def get_target_summary(self, obj):
        if obj.historical_data:
            return f"Historical: {obj.historical_data.category} ({obj.historical_data.date_range_start} - {obj.historical_data.date_range_end})"
        if obj.archived_user:
            return f"Archived User: {obj.archived_user.user.institute_id} ({obj.archived_user.user.full_name})"
        return "Unknown"


class PurgeRequestCreateSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(choices=["historical_data", "archived_user"])
    target_id = serializers.IntegerField()
    reason = serializers.CharField(min_length=3)
    regulatory_authorization_ref = serializers.CharField(min_length=3)


class PurgeAuthorizeSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approve", "reject"])
    comments = serializers.CharField(min_length=3)


class SystemAdminAuditLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAdminAuditLog
        fields = "__all__"


class SessionLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = SessionLog
        fields = "__all__"


class SecurityAlertSerializer(serializers.ModelSerializer):
    class Meta:
        model = SecurityAlert
        fields = "__all__"


class AdminNotificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AdminNotification
        fields = "__all__"


class SystemAdminConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemAdminConfig
        fields = "__all__"


class ConfigUpdateSerializer(serializers.Serializer):
    value = serializers.JSONField()
    confirmation_token = serializers.CharField(required=False, allow_blank=True, default="")
