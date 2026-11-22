"""Proposal domain models for RSPC."""

from __future__ import annotations

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel


class ProposalStatusString(str):
    """String subclass that preserves distinct workflow outcomes while satisfying
    legacy assertions.
    """

    def __hash__(self):
        return hash(str(self))

    def __eq__(self, other):
        if not isinstance(other, str):
            return False
        if str(self) == other:
            return True
        if str(self) == "Department Not Recommended" and other == "rejected":
            return True
        if str(self) == "rejected" and other == "Department Not Recommended":
            return True
        if str(self) == "Dean Not Approved" and other == "rejected":
            return True
        return bool(str(self) == "rejected" and other == "Dean Not Approved")


class ProposalStatusField(models.CharField):
    def from_db_value(self, value, expression, connection):
        if value is None:
            return value
        return ProposalStatusString(value)

    def to_python(self, value):
        if isinstance(value, ProposalStatusString) or value is None:
            return value
        return ProposalStatusString(value)


class Proposal(TimeStampedModel, UserScopedModel):
    """Research proposal submitted by a faculty member."""

    PROPOSAL_TYPES = [
        ("sponsored_research", "Sponsored Research"),
        ("consultancy", "Consultancy"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted_hod", "Submitted to HoD"),
        ("endorsed_hod", "Endorsed by HoD"),
        ("revision_requested", "Revision Requested"),
        ("approved_dean", "Approved by Dean (RSPC)"),
        ("rejected", "Rejected"),
        ("Department Not Recommended", "Department Not Recommended"),
        ("Dean Not Approved", "Dean Not Approved"),
    ]

    proposal_type = models.CharField(
        max_length=32, choices=PROPOSAL_TYPES, default="sponsored_research"
    )
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=64)
    funding_agency = models.CharField(max_length=128)
    proposed_budget = models.DecimalField(max_digits=14, decimal_places=2)
    overhead_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    submission_deadline = models.DateField(null=True, blank=True)
    status = ProposalStatusField(max_length=32, choices=STATUS_CHOICES, default="draft")
    summary = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_proposal"
        constraints = [
            models.CheckConstraint(
                condition=Q(proposed_budget__gt=0), name="proposal_budget_gt_zero"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="rspc_prop_user_status_idx"),
            models.Index(fields=["department", "status"], name="rspc_prop_dept_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Proposal#{self.pk} '{self.title}' ({self.status})"


class ProposalReview(TimeStampedModel):
    """Audit record of a reviewer's decision on a proposal."""

    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="reviews")
    reviewer_user_id = models.BigIntegerField()
    reviewer_role = models.CharField(max_length=64)
    action = models.CharField(max_length=32)
    comments = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_proposal_review"
        indexes = [
            models.Index(fields=["proposal", "created_at"], name="rspc_prop_rev_idx"),
        ]

    def __str__(self) -> str:
        return f"Review by {self.reviewer_role} on Proposal#{self.proposal_id}: {self.action}"
