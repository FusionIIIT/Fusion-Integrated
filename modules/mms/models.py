"""MMS models.

No FK to any user table — user_id is a plain integer (ADR-0013).
No FK to any other module's models.

RegistrationWindow — opened by Caretaker (UC-002).
RegistrationRequest — submitted by Student (UC-003), reviewed by Caretaker (UC-004).
"""
from django.db import models

from core.db.mixins import TimeStampedModel


class RegistrationWindow(TimeStampedModel):
    """A period during which students may submit registration requests.

    Opened by the Mess Caretaker.  Only one window should be open at a time
    (enforced in the service layer — there is no active-period overlap
    constraint in the DB because partial-overlap detection is cheaper in
    Python with a single SELECT).
    """

    opened_by_user_id = models.IntegerField(db_index=True)
    label = models.CharField(max_length=120)       # e.g. "Odd Semester 2026-27"
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()

    class Meta:
        db_table = "mms_registration_window"
        ordering = ["-opens_at"]

    def __str__(self) -> str:
        return self.label

    @property
    def is_open(self) -> bool:
        from django.utils import timezone
        now = timezone.now()
        return self.opens_at <= now <= self.closes_at


class RegistrationRequest(TimeStampedModel):
    """A student's request to register for mess service (UC-003 / UC-004).

    Status lifecycle:
        pending  →  approved  (Caretaker approves — UC-004)
        pending  →  rejected  (Caretaker rejects  — UC-004)
    Once decided, it cannot be decided again (A1 in UC-004).
    """

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    ]

    window = models.ForeignKey(
        RegistrationWindow,
        on_delete=models.PROTECT,
        related_name="requests",
    )
    student_user_id = models.IntegerField(db_index=True)
    remarks = models.TextField(
        max_length=500,
        blank=True,
        help_text="Optional note from the student at submission time.",
    )
    status = models.CharField(
        max_length=16,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_note = models.CharField(max_length=300, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_registration_request"
        # A student may have at most one pending or approved request per window.
        # Duplicate submission is a business error caught in the service.
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["student_user_id", "status"],
                name="mms_reg_student_status_idx",
            ),
            models.Index(
                fields=["window", "status"],
                name="mms_reg_window_status_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"RegistrationRequest({self.id}, student={self.student_user_id}, {self.status})"
