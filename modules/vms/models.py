"""Visitor Management System tables (SRS section 3.14).

Institute users are referenced by plain `*_user_id` integers, never foreign
keys. Foreign keys here stay inside the vms app.
"""
from django.db import models


class Zone(models.Model):
    """A campus area a pass may allow (VMS-BR-191 unauthorized zone access)."""
    name = models.CharField(max_length=80, unique=True)
    is_restricted = models.BooleanField(default=False)


class AccessPolicy(models.Model):
    """Versioned visit limits; only a published version applies (VMS-BR-125, BR-127)."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        PUBLISHED = "published"

    version = models.PositiveIntegerField(unique=True)
    max_visit_hours = models.PositiveSmallIntegerField(default=8)
    walk_in_pass_hours = models.PositiveSmallIntegerField(default=4)
    approval_timeout_hours = models.PositiveSmallIntegerField(default=24)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.DRAFT)
    published_at = models.DateTimeField(null=True, blank=True)


class Visitor(models.Model):
    """An external person visiting the campus."""
    full_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    id_doc_type = models.CharField(max_length=30, blank=True)
    id_doc_number = models.CharField(max_length=60, blank=True, db_index=True)


class VisitRequest(models.Model):
    """A host's request to receive a visitor; approved or rejected by staff."""

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"
        EXPIRED = "expired"      # approval_timeout_hours elapsed undecided
        COMPLETED = "completed"

    visitor = models.ForeignKey(Visitor, on_delete=models.PROTECT,
                                related_name="requests")
    host_user_id = models.IntegerField(db_index=True)
    purpose = models.CharField(max_length=255)
    scheduled_start = models.DateTimeField()
    scheduled_end = models.DateTimeField()
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.PENDING, db_index=True)
    requested_zones = models.ManyToManyField(Zone, blank=True,
                                             related_name="requests")
    decision_note = models.CharField(max_length=255, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class VisitPass(models.Model):
    """Gate credential: QR token plus OTP, valid for a window."""

    class PassType(models.TextChoices):
        PRE_REGISTERED = "PRE_REGISTERED"
        WALK_IN = "WALK_IN"      # short validity, walk_in_pass_hours
        VIP = "VIP"

    visit_request = models.ForeignKey(VisitRequest, on_delete=models.PROTECT,
                                      related_name="passes")
    pass_type = models.CharField(max_length=16, choices=PassType.choices)
    qr_token = models.CharField(max_length=64, unique=True)
    otp = models.CharField(max_length=8)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    allowed_zones = models.ManyToManyField(Zone, blank=True,
                                           related_name="passes")
    issued_by_user_id = models.IntegerField()


class VisitLog(models.Model):
    """Append-only gate event trail."""

    class Event(models.TextChoices):
        CHECK_IN = "check_in"
        CHECK_OUT = "check_out"
        DENIED = "denied"

    visit_pass = models.ForeignKey(VisitPass, on_delete=models.PROTECT,
                                   related_name="logs")
    event = models.CharField(max_length=10, choices=Event.choices)
    zone = models.ForeignKey(Zone, null=True, blank=True,
                             on_delete=models.PROTECT)
    reason = models.CharField(max_length=255, blank=True)
    logged_by_user_id = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class BlacklistEntry(models.Model):
    """A person barred from entry; matched on ID, phone or email."""
    name = models.CharField(max_length=150)
    id_doc_number = models.CharField(max_length=60, blank=True, db_index=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    reason = models.CharField(max_length=255)
    severity = models.CharField(max_length=20, default="high")
    expiry_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
