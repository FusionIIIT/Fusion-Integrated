"""Project domain models for RSPC."""

from __future__ import annotations

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class Project(TimeStampedModel, UserScopedModel):
    """Sanctioned Sponsored Research or Consultancy Project."""

    PROJECT_TYPES = [
        ("sponsored", "Sponsored Research"),
        ("consultancy", "Consultancy"),
    ]

    STATUS_CHOICES = [
        ("sanctioned", "Sanctioned"),
        ("active", "Active"),
        ("extension_requested", "Extension Requested"),
        ("closure_pending", "Closure Pending"),
        ("closed", "Closed"),
        ("terminated", "Terminated"),
    ]

    project_code = models.CharField(max_length=64, unique=True)
    project_type = models.CharField(max_length=32, choices=PROJECT_TYPES, default="sponsored")
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=64)
    funding_agency = models.CharField(max_length=128)
    sanction_order_no = models.CharField(max_length=128)
    sanction_date = models.DateField()
    start_date = models.DateField()
    end_date = models.DateField()
    sanctioned_amount = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(max_length=32, choices=STATUS_CHOICES, default="sanctioned")

    class Meta:
        db_table = "rspc_project"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")), name="rspc_proj_end_gte_start"
            ),
            models.CheckConstraint(
                condition=Q(sanctioned_amount__gt=0), name="rspc_proj_amount_gt_zero"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="rspc_proj_user_status_idx"),
            models.Index(fields=["department", "status"], name="rspc_proj_dept_status_idx"),
            models.Index(fields=["project_code"], name="rspc_proj_code_idx"),
        ]

    def __str__(self) -> str:
        return f"Project {self.project_code} - {self.title} ({self.status})"


class ProjectCoPI(TimeStampedModel):
    """Co-Principal Investigator attached to an RSPC project."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="co_pis")
    user_id = models.BigIntegerField()
    department = models.CharField(max_length=64, blank=True)
    share_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)

    class Meta:
        db_table = "rspc_project_copi"
        constraints = [
            models.UniqueConstraint(
                fields=["project", "user_id"], name="rspc_copi_unique_per_project"
            ),
        ]

    def __str__(self) -> str:
        return f"Co-PI u{self.user_id} on {self.project_id}"
