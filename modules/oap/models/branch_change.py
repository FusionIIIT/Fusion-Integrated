"""Domain model and allocation rules for undergraduate branch changes."""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from modules.oap.domain.exceptions import InvalidStateTransitionError


class BranchChangeStatus(models.TextChoices):
    SUBMITTED = "SUBMITTED", "Submitted by Student"
    VERIFIED_ELIGIBLE = "VERIFIED_ELIGIBLE", "Verified Eligible"
    INELIGIBLE = "INELIGIBLE", "Ineligible per Policy"
    ALLOCATED = "ALLOCATED", "Seat Allocated"
    APPROVED = "APPROVED", "Sanctioned by Dean"
    REJECTED = "REJECTED", "Rejected / Unallocated"


class BranchChangeRequest(models.Model):
    student_id = models.CharField(max_length=32, unique=True, db_index=True)
    current_branch = models.CharField(max_length=32)
    preferred_branch_1 = models.CharField(max_length=32)
    preferred_branch_2 = models.CharField(max_length=32, default="", blank=True)
    current_cpi = models.DecimalField(max_digits=4, decimal_places=2)
    credits_completed = models.IntegerField(default=0)
    has_backlogs = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32,
        choices=BranchChangeStatus.choices,
        default=BranchChangeStatus.SUBMITTED,
    )
    allocated_branch = models.CharField(max_length=32, default="", blank=True)
    approved_by = models.CharField(max_length=32, default="", blank=True)
    remarks = models.TextField(default="", blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "oap_branch_change_request"
        ordering = ["-current_cpi"]

    def __str__(self):
        return (
            f"BranchChange {self.student_id}: {self.current_branch} "
            f"-> {self.preferred_branch_1} ({self.status})"
        )

    def verify_eligibility(
        self, min_cpi: Decimal = Decimal("8.00"), min_credits: int = 36
    ) -> bool:
        if (
            self.current_cpi < min_cpi
            or self.credits_completed < min_credits
            or self.has_backlogs
        ):
            self.status = BranchChangeStatus.INELIGIBLE
            self.remarks = (
                "Did not satisfy CPI (>=8.0), credit (>=36), or clean backlog criteria."
            )
            self.save(update_fields=["status", "remarks"])
            return False
        self.status = BranchChangeStatus.VERIFIED_ELIGIBLE
        self.save(update_fields=["status"])
        return True

    def allocate_seat(self, allocated_branch: str):
        if self.status != BranchChangeStatus.VERIFIED_ELIGIBLE:
            raise InvalidStateTransitionError(
                f"Cannot allocate seat to candidate in status '{self.status}'."
            )
        self.allocated_branch = allocated_branch
        self.status = BranchChangeStatus.ALLOCATED
        self.save(update_fields=["allocated_branch", "status"])

    def sanction(self, approved_by: str, remarks: str = ""):
        if self.status != BranchChangeStatus.ALLOCATED:
            msg = (
                f"Cannot sanction branch change that has not been allocated. "
                f"Current status: '{self.status}'."
            )
            raise InvalidStateTransitionError(msg)
        self.status = BranchChangeStatus.APPROVED
        self.approved_by = approved_by
        self.remarks = remarks
        self.save(update_fields=["status", "approved_by", "remarks"])
