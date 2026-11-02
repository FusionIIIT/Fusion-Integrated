"""Access policy, integration settings, blacklist and safe list."""
import datetime

from django.db import models

from .base import choice_check


class AccessPolicy(models.Model):
    """Versioned visit limits; only a published version applies (VMS-BR-125, BR-127)."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    visiting_hours_start = models.TimeField(default=datetime.time(8, 0))
    visiting_hours_end = models.TimeField(default=datetime.time(20, 0))
    max_visit_hours = models.PositiveSmallIntegerField(default=8)
    walk_in_pass_hours = models.PositiveSmallIntegerField(default=4)
    approval_timeout_hours = models.PositiveSmallIntegerField(default=24)
    reminder_after_hours = models.PositiveSmallIntegerField(default=12)  # D-5: 50 %
    advance_registration_hours = models.PositiveSmallIntegerField(default=2)
    allow_same_day_urgent = models.BooleanField(default=True)
    contingency_sla_minutes = models.PositiveSmallIntegerField(default=15)  # D-13
    walkin_rate_limit_per_hour = models.PositiveSmallIntegerField(default=30)
    restricted_zones = models.ManyToManyField("vms.Zone", blank=True,
                                              related_name="restricting_policies")
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_policy_status_valid")]


class IntegrationSetting(models.Model):
    """Key/value integration config (VMS-CFR-003), e.g. sms_gateway."""
    key = models.CharField(max_length=80, unique=True)
    value = models.JSONField(default=dict, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)


class BlacklistVersion(models.Model):
    """Only the PUBLISHED version is consulted (VMS-BR-120)."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    version = models.PositiveIntegerField(unique=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_blver_status_valid")]


class BlacklistEntry(models.Model):
    """A person barred from entry; matched on ID, phone or email (D-2)."""

    class Severity(models.TextChoices):
        LOW = "low"
        MEDIUM = "medium"
        HIGH = "high"
        CRITICAL = "critical"

    version = models.ForeignKey(BlacklistVersion, null=True, blank=True,
                                on_delete=models.PROTECT, related_name="entries")
    name = models.CharField(max_length=150)
    id_doc_number = models.CharField(max_length=60, blank=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, choices=Severity.choices,
                                default=Severity.HIGH)
    expiry_date = models.DateField(null=True, blank=True)   # "valid until"
    is_active = models.BooleanField(default=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("severity", Severity, "vms_bl_severity_valid")]


class SafeListEntry(models.Model):
    """Explicit exemption from the blacklist; mandatory expiry (BR-118/119, D-7)."""
    visitor_id_doc_number = models.CharField(max_length=60, db_index=True)
    reason = models.CharField(max_length=255)
    expires_at = models.DateTimeField()
    created_by_user_id = models.IntegerField()
    revoked_at = models.DateTimeField(null=True, blank=True)
