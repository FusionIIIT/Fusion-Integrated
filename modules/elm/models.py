"""ELM's own tables. No cross-module ForeignKey (see repo README / ops/checks) —
`applicant_user_id` / `substitute_user_id` are plain IAM user ids, resolved
through modules.directory.contracts when a name/profile is needed.

Scope note (Phase 2, Assignment 6B): category set, half-day CL, Station Leave,
substitute nomination, and the CL/RH lifecycle (submit -> Unit Head decision
-> withdraw/cancel) are implemented per the ELM Business Rule Specifications
(BR-EL-001, 010, 012, 013, 014, 015, 016, 022, 023, 024, 034). Entitlement
accounting/balances, year-end processing, SLA reminders/escalation, and the
full Dean/Registrar/Director higher-sanction hierarchy for SCL/EL/COL/VL are
NOT implemented — see modules/elm/UNRESOLVED.md.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class Category(models.TextChoices):
    """BR-EL-001: the only supported leave categories in this baseline."""

    CL = "CL", "Casual Leave"
    RH = "RH", "Restricted Holiday"
    SCL = "SCL", "Special Casual Leave"
    EL = "EL", "Earned Leave"
    COL = "COL", "Commuted Leave"
    VL = "VL", "Vacation Leave"


#: BR-EL-011: continuous counting (weekends/holidays count as leave days)
#: applies only to these three categories.
CONTINUOUS_COUNT_CATEGORIES = frozenset({Category.EL, Category.COL, Category.VL})

#: BR-EL-010: only CL supports a half-day request in this baseline.
HALF_DAY_ELIGIBLE_CATEGORIES = frozenset({Category.CL})


class HalfDay(models.TextChoices):
    NONE = "none", "Full day"
    FIRST = "first_half", "First half"
    SECOND = "second_half", "Second half"


class Status(models.TextChoices):
    """CL/RH path (BR-EL-016, Unit Head is final): PENDING -> APPROVED/REJECTED.
    SCL/EL/COL/VL path (BR-EL-017): PENDING -> UNIT_HEAD_RECOMMENDED or
    UNIT_HEAD_NOT_RECOMMENDED, then STOPS — see UNRESOLVED.md; it does not
    reach APPROVED/REJECTED in this build because the configured
    Dean/Registrar/Director routing (BR-EL-018/019) is not implemented and
    faking a final decision there would misrepresent an unenforced rule.
    WITHDRAWN (BR-EL-022/034) and CANCELLED (BR-EL-023) apply to both paths.
    """

    PENDING = "pending", "Pending"
    UNIT_HEAD_RECOMMENDED = "unit_head_recommended", "Unit Head: Recommended"
    UNIT_HEAD_NOT_RECOMMENDED = "unit_head_not_recommended", "Unit Head: Not Recommended"
    APPROVED = "approved", "Approved"
    REJECTED = "rejected", "Rejected"
    WITHDRAWN = "withdrawn", "Withdrawn"
    CANCELLED = "cancelled", "Cancelled"


class SubstituteConsent(models.TextChoices):
    NOT_REQUIRED = "not_required", "Not required"
    PENDING = "pending", "Pending"
    ACCEPTED = "accepted", "Accepted"
    DECLINED = "declined", "Declined"


class LeaveRequest(TimeStampedModel):
    """One leave application. `applicant_user_id` / `substitute_user_id` /
    `unit_head_user_id` are IAM user ids (see module docstring)."""

    applicant_user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=Category.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=16, choices=HalfDay.choices, default=HalfDay.NONE
    )
    #: BR-EL-013: Station Leave is captured inside this application, not a
    #: separate process.
    station_leave = models.BooleanField(default=False)
    station_leave_details = models.CharField(max_length=255, blank=True)
    reason = models.TextField(blank=True)

    status = models.CharField(
        max_length=32, choices=Status.choices, default=Status.PENDING, db_index=True
    )

    #: Who decides for this request (resolved at submission time from the
    #: applicant's organisational unit). Required for BR-EL-016/017 routing.
    unit_head_user_id = models.IntegerField()
    unit_head_decided_at = models.DateTimeField(null=True, blank=True)
    unit_head_remarks = models.TextField(blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_consent = models.CharField(
        max_length=16,
        choices=SubstituteConsent.choices,
        default=SubstituteConsent.NOT_REQUIRED,
    )

    withdrawn_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["applicant_user_id", "status"]),
            models.Index(fields=["unit_head_user_id", "status"]),
        ]

    def __str__(self) -> str:
        return f"{self.category} leave #{self.pk} for user {self.applicant_user_id}"
