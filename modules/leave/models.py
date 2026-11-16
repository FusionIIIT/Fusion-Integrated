"""Database models for Leave Management (ELM).

Per platform rules:
- No foreign keys cross module boundaries (cross-boundary references use plain user_id integers).
- Foreign keys within the leave module (e.g. ApprovalDecision -> LeaveRequest) are permitted.
"""
from __future__ import annotations

from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.leave.domain.entities import ApprovalOutcome, AuthorityRole, LeaveStatus, LeaveType


class LeaveRequest(TimeStampedModel, UserScopedModel):
    class Status(models.TextChoices):
        DRAFT = LeaveStatus.DRAFT.value, "Draft"
        PENDING_CURRENT_AUTHORITY = (
            LeaveStatus.PENDING_CURRENT_AUTHORITY.value,
            "Pending Current Authority",
        )
        APPROVED = LeaveStatus.APPROVED.value, "Approved"
        REJECTED = LeaveStatus.REJECTED.value, "Rejected"
        CANCELLED = LeaveStatus.CANCELLED.value, "Cancelled"

    class LeaveTypes(models.TextChoices):
        CASUAL = LeaveType.CASUAL.value, "Casual Leave"
        RESTRICTED = LeaveType.RESTRICTED.value, "Restricted Holiday"
        MEDICAL = LeaveType.MEDICAL.value, "Medical Leave"
        EARNED = LeaveType.EARNED.value, "Earned Leave"
        VACATION = LeaveType.VACATION.value, "Vacation Leave"
        SABBATICAL = LeaveType.SABBATICAL.value, "Sabbatical Leave"

    leave_type = models.CharField(
        max_length=32,
        choices=LeaveTypes.choices,
        db_index=True,
    )
    start_date = models.DateField()
    end_date = models.DateField()
    duration_days = models.DecimalField(max_digits=5, decimal_places=1)
    justification = models.TextField()
    status = models.CharField(
        max_length=40,
        choices=Status.choices,
        default=Status.PENDING_CURRENT_AUTHORITY,
        db_index=True,
    )
    current_authority_id = models.IntegerField(null=True, blank=True, db_index=True)
    current_authority_role = models.CharField(max_length=40, blank=True)
    forward_count = models.PositiveSmallIntegerField(default=0)
    cancellation_reason = models.TextField(blank=True)
    submission_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_request"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_req_user_st_idx"),
            models.Index(
                fields=["current_authority_id", "status"],
                name="leave_req_auth_st_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"LeaveRequest #{self.id} (user {self.user_id}, {self.leave_type}, {self.status})"


class LeaveBalance(TimeStampedModel, UserScopedModel):
    class LeaveTypes(models.TextChoices):
        CASUAL = LeaveType.CASUAL.value, "Casual Leave"
        RESTRICTED = LeaveType.RESTRICTED.value, "Restricted Holiday"
        MEDICAL = LeaveType.MEDICAL.value, "Medical Leave"
        EARNED = LeaveType.EARNED.value, "Earned Leave"
        VACATION = LeaveType.VACATION.value, "Vacation Leave"
        SABBATICAL = LeaveType.SABBATICAL.value, "Sabbatical Leave"

    leave_type = models.CharField(
        max_length=32,
        choices=LeaveTypes.choices,
        db_index=True,
    )
    year = models.PositiveSmallIntegerField(db_index=True)
    total_entitlement = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("12.0"),
    )
    consumed_days = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("0.0"),
    )
    available_balance = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=Decimal("12.0"),
    )

    class Meta:
        db_table = "leave_balance"
        unique_together = (("user_id", "leave_type", "year"),)
        ordering = ["year", "leave_type"]

    def __str__(self) -> str:
        return (
            f"LeaveBalance (user {self.user_id}, {self.leave_type}, "
            f"year {self.year}: avail {self.available_balance})"
        )


class ApprovalDecision(TimeStampedModel):
    class Outcome(models.TextChoices):
        APPROVED = ApprovalOutcome.APPROVED.value, "Approved"
        REJECTED = ApprovalOutcome.REJECTED.value, "Rejected"
        FORWARDED = ApprovalOutcome.FORWARDED.value, "Forwarded"

    request = models.ForeignKey(
        LeaveRequest,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    authority_id = models.IntegerField(db_index=True)
    next_authority_id = models.IntegerField(null=True, blank=True)
    outcome = models.CharField(max_length=32, choices=Outcome.choices)
    remarks = models.TextField(blank=True)
    decided_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_approval_decision"
        ordering = ["-decided_at"]

    def __str__(self) -> str:
        return (
            f"Decision for Req #{self.request_id} by Auth #{self.authority_id}: "
            f"{self.outcome}"
        )


class ApprovingAuthority(TimeStampedModel):
    class Roles(models.TextChoices):
        HOD = AuthorityRole.HOD.value, "Head of Department"
        REGISTRAR = AuthorityRole.REGISTRAR.value, "Registrar"
        DIRECTOR = AuthorityRole.DIRECTOR.value, "Director"

    user_id = models.IntegerField(unique=True, db_index=True)
    role = models.CharField(max_length=40, choices=Roles.choices)
    department = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_approving_authority"

    def __str__(self) -> str:
        return f"ApprovingAuthority #{self.user_id} ({self.role}, dept={self.department})"
