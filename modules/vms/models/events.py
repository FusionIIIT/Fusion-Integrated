"""Extensions, emergency muster and bulk event batches."""
from django.db import models

from .base import choice_check


class ExtensionRequest(models.Model):
    """Host asks to extend a visit (VMS-CFR-030)."""

    class Status(models.TextChoices):
        PENDING = "pending"
        APPROVED = "approved"
        REJECTED = "rejected"

    visit_request = models.ForeignKey("vms.VisitRequest", on_delete=models.PROTECT,
                                      related_name="extensions")
    requested_end = models.DateTimeField()
    reason = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.PENDING)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_ext_status_valid")]


class EmergencyMuster(models.Model):
    """An emergency roll call (VMS-CFR-018)."""

    class Status(models.TextChoices):
        OPEN = "open"
        CLOSED = "closed"

    triggered_by_user_id = models.IntegerField()
    trigger_role = models.CharField(max_length=30, blank=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=10, choices=Status.choices,
                              default=Status.OPEN)
    closed_at = models.DateTimeField(null=True, blank=True)
    summary = models.JSONField(default=dict, blank=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_muster_status_valid")]


class MusterEntry(models.Model):
    """One person on a muster list."""

    class Status(models.TextChoices):
        UNACCOUNTED = "unaccounted"
        ACCOUNTED = "accounted"
        EVACUATED = "evacuated"

    muster = models.ForeignKey(EmergencyMuster, on_delete=models.CASCADE,
                               related_name="entries")
    visit_pass = models.ForeignKey("vms.VisitPass", on_delete=models.PROTECT,
                                   related_name="muster_entries")
    last_zone = models.ForeignKey("vms.Zone", null=True, blank=True,
                                  on_delete=models.PROTECT, related_name="+")
    last_seen_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.UNACCOUNTED)
    marked_by_user_id = models.IntegerField(null=True, blank=True)
    marked_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        pass

    Meta.constraints = [
        choice_check("status", Status, "vms_musterentry_status_valid"),
        models.UniqueConstraint(fields=["muster", "visit_pass"],
                                name="vms_musterentry_unique_pass"),
    ]


class EventBatch(models.Model):
    """A bulk event registration (VMS-CFR-009)."""

    class Status(models.TextChoices):
        DRAFT = "draft"
        ACTIVE = "active"
        CLOSED = "closed"
        CANCELLED = "cancelled"

    name = models.CharField(max_length=150)
    organizer = models.CharField(max_length=150, blank=True)
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    zones = models.ManyToManyField("vms.Zone", blank=True,
                                   related_name="event_batches")
    slots = models.JSONField(default=list, blank=True)   # [{start, end, capacity}]
    fast_lane = models.BooleanField(default=False)
    walkin_rate_limit = models.PositiveSmallIntegerField(null=True, blank=True)
    created_by_user_id = models.IntegerField()
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_event_status_valid")]


class EventAttendee(models.Model):
    """One attendee on an event batch."""

    class Status(models.TextChoices):
        INVITED = "invited"
        PASS_ISSUED = "pass_issued"  # noqa: S105
        CHECKED_IN = "checked_in"
        CANCELLED = "cancelled"

    batch = models.ForeignKey(EventBatch, on_delete=models.CASCADE,
                              related_name="attendees")
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    id_doc_type = models.CharField(max_length=30, blank=True)
    id_doc_number = models.CharField(max_length=60, blank=True)
    slot_start = models.DateTimeField(null=True, blank=True)
    slot_end = models.DateTimeField(null=True, blank=True)
    visit_pass = models.ForeignKey("vms.VisitPass", null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="+",
                                   db_column="pass_id")
    status = models.CharField(max_length=12, choices=Status.choices,
                              default=Status.INVITED)

    class Meta:
        pass

    Meta.constraints = [choice_check("status", Status, "vms_attendee_status_valid")]
