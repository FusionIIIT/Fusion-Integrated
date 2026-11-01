"""Database models for Institute Works Department (IWD) module.

Per ADR-0013 and platform conventions:
- Institute persons are referenced by plain integer `user_id` values, never cross-module FKs.
- Domain-specific stakeholder rosters (IWD Engineer trade specialization) are local to IWD.
- All state changes are tracked in an append-only audit model (ComplaintTransition).
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel
from modules.iwd.domain.cost_bands import CostBand
from modules.iwd.domain.state_machine import IWDState


class Engineer(TimeStampedModel):
    """Local roster of IWD engineers and their trade specializations.

    Tracks whether an engineer is active and whether their expertise is in
    civil or electrical maintenance work orders (BR-IWD-002, CFR-IWD-02).
    """

    SPECIALIZATION_CHOICES = [
        ("civil", "Civil"),
        ("electrical", "Electrical"),
    ]

    user_id = models.IntegerField(unique=True, db_index=True)
    specialization = models.CharField(
        max_length=20,
        choices=SPECIALIZATION_CHOICES,
        db_index=True,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "iwd_engineer"
        indexes = [
            models.Index(fields=["specialization", "is_active"], name="iwd_eng_spec_active_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(specialization__in=["civil", "electrical"]),
                name="iwd_engineer_specialization_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Engineer u{self.user_id} ({self.specialization})"


class Complaint(TimeStampedModel):
    """Maintenance complaint submitted by an Institute Employee.

    Follows CFR-IWD-01 (AFR-IWD-001 through AFR-IWD-006) and BR-IWD-001/002.
    """

    CATEGORY_CHOICES = [
        ("civil", "Civil"),
        ("electrical", "Electrical"),
    ]

    URGENCY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("emergency", "Emergency"),
    ]

    user_id = models.IntegerField(db_index=True)  # IAM complainant user_id (ADR-0013)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    location = models.CharField(max_length=255)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES, default="low")
    remarks = models.TextField(blank=True)
    status = models.CharField(
        max_length=64,
        choices=[(s.value, s.value) for s in IWDState],
        default=IWDState.SUBMITTED.value,
        db_index=True,
    )
    assigned_engineer_id = models.IntegerField(null=True, blank=True, db_index=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    assessment_details = models.TextField(blank=True, default="")
    assessed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iwd_complaint"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="iwd_complaint_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="iwd_complaint_user_idx"),
            models.Index(fields=["assigned_engineer_id", "status"], name="iwd_complaint_eng_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(status__in=[s.value for s in IWDState]),
                name="iwd_complaint_status_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(category__in=["civil", "electrical"]),
                name="iwd_complaint_category_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(urgency__in=["low", "medium", "high", "emergency"]),
                name="iwd_complaint_urgency_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Complaint #{self.pk} u{self.user_id} [{self.status}]"


class ComplaintTransition(models.Model):
    """Append-only audit trail of complaint lifecycle transitions (CFR-IWD-11)."""

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=64)
    to_status = models.CharField(max_length=64)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_complaint_transition"
        indexes = [
            models.Index(fields=["complaint", "-created_at"], name="iwd_trans_complaint_idx"),
        ]

    def __str__(self) -> str:
        return f"Complaint #{self.complaint_id} {self.from_status}->{self.to_status}"


class Estimate(TimeStampedModel):
    """Repair estimate prepared and submitted by an Engineer for an assessed complaint.

    Covers time, materials, cost, and routing band (AFR-IWD-011..014, BR-IWD-003, UC-IWD-021).
    """

    COST_BAND_CHOICES = [
        (CostBand.LOW.value, "Low-Cost (< ₹25,000)"),
        (CostBand.MID.value, "Mid-Range (₹25,000 - ₹2,50,000)"),
        (CostBand.HIGH.value, "High-Cost (> ₹2,50,000)"),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="estimates",
    )
    engineer_id = models.IntegerField(db_index=True)
    cost_band = models.CharField(max_length=20, choices=COST_BAND_CHOICES)
    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2)
    estimated_time = models.CharField(max_length=120)
    materials_summary = models.TextField()
    supporting_details = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_estimate"
        indexes = [
            models.Index(fields=["complaint", "-created_at"], name="iwd_estimate_complaint_idx"),
            models.Index(fields=["engineer_id", "-created_at"], name="iwd_estimate_engineer_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estimated_cost__gt=0),
                name="iwd_estimate_cost_positive",
            ),
            models.CheckConstraint(
                condition=models.Q(cost_band__in=[b.value for b in CostBand]),
                name="iwd_estimate_cost_band_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"Estimate #{self.pk} for Complaint #{self.complaint_id} [₹{self.estimated_cost}]"


class MaterialIssue(TimeStampedModel):
    """Auditable record of materials issued from stock or procurement for approved work (BR-IWD-011, AFR-IWD-029)."""

    SOURCE_CHOICES = [
        ("stock", "Warehouse Stock"),
        ("procurement", "Stock Shortage Procurement"),
    ]

    complaint = models.ForeignKey(
        Complaint,
        on_delete=models.CASCADE,
        related_name="material_issues",
    )
    admin_user_id = models.IntegerField(db_index=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    materials_summary = models.TextField()
    remarks = models.TextField(blank=True, default="")
    issued_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_material_issue"
        indexes = [
            models.Index(fields=["complaint", "-created_at"], name="iwd_mat_issue_complaint_idx"),
            models.Index(fields=["admin_user_id", "-created_at"], name="iwd_mat_issue_admin_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(source__in=["stock", "procurement"]),
                name="iwd_material_issue_source_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"MaterialIssue #{self.pk} for Complaint #{self.complaint_id} ({self.source})"

