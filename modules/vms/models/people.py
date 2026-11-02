"""Visitors and the people-side grants: sessions, roles, VIP, pre-authorisation."""
from django.db import models

from .base import choice_check


class Visitor(models.Model):
    """An external person visiting the campus."""
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    id_doc_type = models.CharField(max_length=30, blank=True)
    id_doc_number = models.CharField(max_length=60, blank=True, db_index=True)
    is_anonymized = models.BooleanField(default=False)   # VMS-CFR-029/032


class VisitorSession(models.Model):
    """Email-OTP visitor login (decision D-1). Only hashes are stored."""
    visitor = models.ForeignKey(Visitor, on_delete=models.CASCADE,
                                related_name="sessions")
    token_hash = models.CharField(max_length=128, unique=True)
    otp_hash = models.CharField(max_length=128, blank=True)
    expires_at = models.DateTimeField()
    verified_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)


class RoleAssignment(models.Model):
    """Time-bound, scoped Admin/Security role (VMS-CFR-002, BR-181..184)."""

    class Role(models.TextChoices):
        ADMIN = "admin"
        SECURITY = "security"

    class ScopeType(models.TextChoices):
        CAMPUS = "campus"
        ZONE = "zone"
        GATE = "gate"

    user_id = models.IntegerField()
    role = models.CharField(max_length=10, choices=Role.choices)
    scope_type = models.CharField(max_length=10, choices=ScopeType.choices,
                                  default=ScopeType.CAMPUS)
    scope_id = models.IntegerField(null=True, blank=True)   # null for campus
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    assigned_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user_id", "role", "ends_at"],
                                name="vms_role_user_role_end_idx")]

    Meta.constraints = [
        choice_check("role", Role, "vms_roleassign_role_valid"),
        choice_check("scope_type", ScopeType, "vms_roleassign_scope_valid"),
        models.CheckConstraint(
            condition=models.Q(scope_type="campus")
            | models.Q(scope_id__isnull=False),
            name="vms_roleassign_scope_id_set"),
        models.CheckConstraint(
            condition=models.Q(ends_at__gt=models.F("starts_at")),
            name="vms_roleassign_window_valid"),
    ]


class VipPermission(models.Model):
    """Super-Admin granted VIP override scope (VMS-CFR-004, D-6, D-16)."""
    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT,
                                related_name="vip_permissions")
    zones = models.ManyToManyField("vms.Zone", blank=True,
                                   related_name="vip_permissions")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    granted_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)


class PreAuthorization(models.Model):
    """A host pre-authorises a visitor for repeat visits (VMS-CFR-011)."""
    host_user_id = models.IntegerField(db_index=True)
    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT,
                                related_name="pre_authorizations")
    zones = models.ManyToManyField("vms.Zone", blank=True,
                                   related_name="pre_authorizations")
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    max_visits = models.PositiveSmallIntegerField(default=1)
    used_visits = models.PositiveSmallIntegerField(default=0)
    revoked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

    Meta.constraints = [models.CheckConstraint(
        condition=models.Q(used_visits__lte=models.F("max_visits")),
        name="vms_preauth_used_le_max")]
