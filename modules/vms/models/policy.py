from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class AccessPolicyVersion(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("published", "Published"), ("retired", "Retired")]
    scope_key = models.CharField(max_length=80, default="campus")
    version = models.PositiveIntegerField()
    status = models.CharField(max_length=12, choices=STATUS, default="draft", db_index=True)
    effective_from = models.DateTimeField()
    effective_until = models.DateTimeField(null=True, blank=True)
    visiting_hours_start = models.TimeField(null=True, blank=True)
    visiting_hours_end = models.TimeField(null=True, blank=True)
    maximum_visit_minutes = models.PositiveIntegerField(default=480)
    walk_in_minutes = models.PositiveIntegerField(default=240)
    approval_timeout_minutes = models.PositiveIntegerField(default=1440)
    contingency_timeout_minutes = models.PositiveIntegerField(default=60)
    advance_registration_minutes = models.PositiveIntegerField(default=0)
    reminder_minutes = models.JSONField(default=list, blank=True)
    restricted_zones = models.JSONField(default=list, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_access_policy_version"
        constraints = [
            models.UniqueConstraint(
                fields=["scope_key", "version"], name="vms_policy_scope_ver_uq"
            ),
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gt=models.F("effective_from")),
                name="vms_policy_effective_window",
            ),
        ]
        indexes = [
            models.Index(
                fields=["scope_key", "status", "effective_from"], name="vms_policy_runtime_idx"
            )
        ]


class RegistryVersion(TimeStampedModel):
    STATUS = [("draft", "Draft"), ("published", "Published"), ("retired", "Retired")]
    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=STATUS, default="draft", db_index=True)
    effective_from = models.DateTimeField()
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_registry_version"
        indexes = [
            models.Index(fields=["status", "effective_from"], name="vms_registry_runtime_idx")
        ]


class BlacklistEntry(TimeStampedModel):
    version = models.ForeignKey(
        RegistryVersion, on_delete=models.PROTECT, related_name="blacklist_entries"
    )
    display_name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, db_index=True)
    identity_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    reason = models.CharField(max_length=500)
    severity = models.CharField(max_length=16, default="standard")
    expires_at = models.DateTimeField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_blacklist_entry"
        indexes = [models.Index(fields=["version", "is_active"], name="vms_blacklist_ver_idx")]


class SafeListEntry(TimeStampedModel):
    version = models.ForeignKey(
        RegistryVersion, on_delete=models.PROTECT, related_name="safe_list_entries"
    )
    display_name = models.CharField(max_length=160)
    normalized_name = models.CharField(max_length=160, db_index=True)
    identity_fingerprint = models.CharField(max_length=64, blank=True, db_index=True)
    reason = models.CharField(max_length=500)
    expires_at = models.DateTimeField(db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "vms_safe_list_entry"
        indexes = [
            models.Index(
                fields=["version", "is_active", "expires_at"], name="vms_safelist_runtime_idx"
            )
        ]


class VipPermission(TimeStampedModel):
    visitor = models.ForeignKey(
        "vms.VisitorProfile", on_delete=models.PROTECT, related_name="vip_permissions"
    )
    visit_request = models.ForeignKey(
        "vms.VisitRequest",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="vip_permissions",
    )
    zones = models.JSONField(default=list, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(db_index=True)
    granted_by_user_id = models.IntegerField()
    reason = models.CharField(max_length=500)
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_vip_permission"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_until__gt=models.F("valid_from")), name="vms_vip_window_valid"
            )
        ]
        indexes = [models.Index(fields=["visitor", "valid_until"], name="vms_vip_runtime_idx")]


class PreAuthorization(TimeStampedModel):
    host_user_id = models.IntegerField(db_index=True)
    visitor = models.ForeignKey(
        "vms.VisitorProfile", on_delete=models.PROTECT, related_name="pre_authorizations"
    )
    zones = models.JSONField(default=list, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField(db_index=True)
    created_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "vms_pre_authorization"
        constraints = [
            models.CheckConstraint(
                condition=Q(valid_until__gt=models.F("valid_from")), name="vms_preauth_window_valid"
            )
        ]
        indexes = [
            models.Index(
                fields=["host_user_id", "visitor", "valid_until"], name="vms_preauth_scope_idx"
            )
        ]


class VmsRoleAssignment(TimeStampedModel):
    ROLE = [("admin", "Admin"), ("security", "Security Personnel")]
    SCOPE = [("campus", "Campus"), ("zone", "Zone"), ("gate", "Gate")]
    user_id = models.IntegerField(db_index=True)
    role = models.CharField(max_length=16, choices=ROLE)
    scope_type = models.CharField(max_length=12, choices=SCOPE)
    scope_value = models.CharField(max_length=100, blank=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField(null=True, blank=True, db_index=True)
    assigned_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    revoked_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_role_assignment"
        constraints = [
            models.CheckConstraint(
                condition=Q(ends_at__isnull=True) | Q(ends_at__gt=models.F("starts_at")),
                name="vms_role_assignment_window",
            )
        ]
        indexes = [models.Index(fields=["user_id", "role", "ends_at"], name="vms_role_runtime_idx")]


class IntegrationSetting(TimeStampedModel):
    TYPE = [
        ("campus_id", "Campus ID"),
        ("directory", "User directory"),
        ("event_management", "Event Management"),
        ("hostel", "Hostel Management"),
        ("access_control", "Access Control"),
        ("notification", "Notifications"),
    ]
    integration_type = models.CharField(max_length=24, choices=TYPE, unique=True)
    endpoint = models.URLField(max_length=500, blank=True)
    enabled = models.BooleanField(default=False)
    available = models.BooleanField(default=False)
    config = models.JSONField(default=dict, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "vms_integration_setting"
