"""Extension and Closure models for RSPC projects."""

from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.rspc.models.project import Project


class ProjectExtensionRequest(TimeStampedModel):
    """Formal request to extend a project's completion deadline."""

    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("hod_recommended", "HoD Recommended"),
        ("dean_approved", "Dean Approved"),
        ("rejected", "Rejected"),
    ]

    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="extension_requests"
    )
    requested_end_date = models.DateField()
    months_requested = models.PositiveSmallIntegerField()
    justification = models.TextField()
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="submitted")
    reviewed_by_user_id = models.BigIntegerField(null=True, blank=True)
    decision_comments = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_extension_request"
        indexes = [
            models.Index(fields=["project", "status"], name="rspc_ext_proj_status_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"Extension for {self.project.project_code} (+{self.months_requested}m: {self.status})"
        )


class ProjectClosureRequest(TimeStampedModel):
    """Formal closure request and No-Objection Certificate (NOC) protocol."""

    STATUS_CHOICES = [
        ("pending", "Closure Pending"),
        ("approved", "Closed & Approved"),
        ("rejected", "Closure Rejected"),
    ]

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name="closure_record")
    utilization_certificate_submitted = models.BooleanField(default=False)
    completion_report_submitted = models.BooleanField(default=False)
    unspent_balance_refunded = models.BooleanField(default=False)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="pending")
    closed_at = models.DateTimeField(null=True, blank=True)
    closed_by_user_id = models.BigIntegerField(null=True, blank=True)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_closure_request"

    def __str__(self) -> str:
        return f"Closure for {self.project.project_code} ({self.status})"
