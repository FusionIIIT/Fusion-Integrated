"""Stay alerts, the duty roster and the notification outbox."""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel
from modules.visitor_hostel.domain import duty


class StayAlert(models.Model):
    """BR-VH-017 / BR-VH-018. Once per booking per kind."""

    NO_SHOW = "no_show"
    OVERSTAY = "overstay"
    KIND = [(NO_SHOW, "No-show"), (OVERSTAY, "Overstay")]

    booking = models.ForeignKey("Booking", on_delete=models.CASCADE,
                                related_name="alerts")
    kind = models.CharField(max_length=10, choices=KIND)
    raised_at = models.DateTimeField(auto_now_add=True)
    expected_at = models.DateTimeField()

    class Meta:
        db_table = "vh_stay_alert"
        constraints = [
            models.UniqueConstraint(fields=["booking", "kind"],
                                    name="vh_stay_alert_once_per_kind"),
        ]
        indexes = [models.Index(fields=["-raised_at"], name="vh_stay_alert_recent_idx")]

    def __str__(self) -> str:
        return f"{self.kind} booking#{self.booking_id}"


class DutyAssignment(models.Model):
    """Who is on duty as Caretaker or VH In-Charge. Not an access-control
    table: the IAM grants the permissions, this picks the one holder."""

    ROLE = [(r, duty.LABELS[r]) for r in duty.ROLES]

    role = models.CharField(max_length=10, choices=ROLE)
    user_id = models.IntegerField()
    valid_from = models.DateTimeField()
    valid_until = models.DateTimeField()
    ended_at = models.DateTimeField(null=True, blank=True)
    assigned_by_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "vh_duty_assignment"
        constraints = [
            # BR-VH-045 / BR-VH-046: exactly one open assignment per role.
            models.UniqueConstraint(fields=["role"], condition=Q(ended_at__isnull=True),
                                    name="vh_one_open_duty_per_role"),
            models.CheckConstraint(condition=Q(valid_until__gt=F("valid_from")),
                                   name="vh_duty_window_ordered"),
            models.CheckConstraint(condition=Q(role__in=duty.ROLES),
                                   name="vh_duty_role_valid"),
        ]
        indexes = [models.Index(fields=["role", "-valid_from"], name="vh_duty_role_idx")]

    def __str__(self) -> str:
        return f"{self.role} u{self.user_id}"


class NotificationOutbox(TimeStampedModel):
    """A notification VHMS decided to send, written in the same transaction as
    its cause and drained by a worker. Delivery infrastructure is outside VHMS
    (AFR-VH-081); this row is the VHMS notification record (AFR-VH-106)."""

    STATUS = [("pending", "Pending"), ("sending", "Sending"), ("sent", "Sent"),
              ("failed", "Failed")]

    topic = models.CharField(max_length=40, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField()
    subject = models.CharField(max_length=200)
    body = models.TextField()
    payload = models.JSONField(default=dict, blank=True)

    status = models.CharField(max_length=10, choices=STATUS, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "vh_notification_outbox"
        indexes = [models.Index(fields=["status", "created_at"],
                                name="vh_outbox_pending_idx")]

    def __str__(self) -> str:
        return f"{self.topic} -> u{self.recipient_user_id}"
