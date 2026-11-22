"""Domain model and state transitions for student leave requests."""
from __future__ import annotations

from django.db import models

from modules.oap.domain.exceptions import InvalidStateTransitionError


class LeaveType(models.TextChoices):
    CASUAL = "CASUAL", "Casual Leave"
    MEDICAL = "MEDICAL", "Medical Leave"
    SHORT = "SHORT", "Short Leave"
    SEMESTER_LEAVE = "SEMESTER_LEAVE", "Semester Leave of Absence"


class RequestStatus(models.TextChoices):
    PENDING = "PENDING", "Pending Review"
    RECOMMENDED = "RECOMMENDED", "Recommended by Supervisor"
    APPROVED = "APPROVED", "Approved"
    REJECTED = "REJECTED", "Rejected"
    CANCELLED = "CANCELLED", "Cancelled by Student"


class StudentLeaveRequest(models.Model):
    student_id = models.CharField(max_length=32, db_index=True)
    student_name = models.CharField(max_length=128)
    leave_type = models.CharField(
        max_length=32, choices=LeaveType.choices, default=LeaveType.CASUAL
    )
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(
        max_length=32, choices=RequestStatus.choices, default=RequestStatus.PENDING
    )
    supervisor_id = models.CharField(max_length=32, default="", blank=True)
    supervisor_remarks = models.TextField(default="", blank=True)
    hod_id = models.CharField(max_length=32, default="", blank=True)
    hod_remarks = models.TextField(default="", blank=True)
    document_url = models.URLField(max_length=512, default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "oap_student_leave_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Leave {self.pk} - {self.student_id} ({self.status})"

    @property
    def duration_days(self) -> int:
        if self.start_date and self.end_date:
            return (self.end_date - self.start_date).days + 1
        return 0

    def recommend(self, supervisor_id: str, remarks: str = ""):
        if self.status != RequestStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Cannot recommend leave in status '{self.status}'."
            )
        self.status = RequestStatus.RECOMMENDED
        self.supervisor_id = supervisor_id
        self.supervisor_remarks = remarks
        self.save(
            update_fields=["status", "supervisor_id", "supervisor_remarks", "updated_at"]
        )

    def hod_approve(self, hod_id: str, remarks: str = ""):
        if self.status not in (RequestStatus.PENDING, RequestStatus.RECOMMENDED):
            raise InvalidStateTransitionError(
                f"Cannot approve leave in terminal status '{self.status}'."
            )
        self.status = RequestStatus.APPROVED
        self.hod_id = hod_id
        self.hod_remarks = remarks
        self.save(update_fields=["status", "hod_id", "hod_remarks", "updated_at"])

    def hod_reject(self, hod_id: str, remarks: str = ""):
        if self.status not in (RequestStatus.PENDING, RequestStatus.RECOMMENDED):
            raise InvalidStateTransitionError(
                f"Cannot reject leave in terminal status '{self.status}'."
            )
        self.status = RequestStatus.REJECTED
        self.hod_id = hod_id
        self.hod_remarks = remarks
        self.save(update_fields=["status", "hod_id", "hod_remarks", "updated_at"])

    def cancel(self):
        if self.status != RequestStatus.PENDING:
            raise InvalidStateTransitionError(
                f"Only pending requests may be cancelled. Current status is '{self.status}'."
            )
        self.status = RequestStatus.CANCELLED
        self.save(update_fields=["status", "updated_at"])
