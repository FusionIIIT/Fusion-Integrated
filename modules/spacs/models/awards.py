"""Convocation awards, candidate evaluations, and cycle transitions for SPACS.

Enforces:
- CFR-SPACS-013 (Award Candidate Sourcing and Pool Preparation)
- CFR-SPACS-014 (Award Evaluation, Approval and Publication)
- BR-SPACS-019 (Award evaluation & approval follow award policy)
- BR-SPACS-020 (Award criteria versioning)
- BR-SPACS-023 (Award candidate source is scheme-specific)
- ADR-0013: Person references are plain integer user_ids, no cross-module foreign keys.
"""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.spacs.domain.state_machines import (
    AWARD_CYCLE_STATUSES,
    AWARD_STATUS_OPEN,
)


class AwardCycle(TimeStampedModel):
    """An annual or convocation cycle for an institute award/prize."""

    policy_version = models.ForeignKey(
        "CataloguePolicyVersion", on_delete=models.PROTECT, related_name="award_cycles"
    )
    convocation_year = models.PositiveIntegerField(db_index=True)  # e.g., 2026
    status = models.CharField(
        max_length=32, choices=AWARD_CYCLE_STATUSES, default=AWARD_STATUS_OPEN, db_index=True
    )

    # Pool Finalization (UC-SPACS-017)
    pool_finalized_at = models.DateTimeField(null=True, blank=True)
    pool_finalized_by_user_id = models.IntegerField(null=True, blank=True)

    # Committee Evaluation Finalization (UC-SPACS-018)
    eval_completed_at = models.DateTimeField(null=True, blank=True)

    # External Institutional Approval Provenance (UC-SPACS-019, BR-SPACS-019)
    approval_authority_recorded = models.CharField(max_length=120, blank=True)
    approval_reference_recorded = models.CharField(max_length=150, blank=True)
    approval_recorded_at = models.DateTimeField(null=True, blank=True)

    # Official Publication (UC-SPACS-020)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_award_cycle"
        ordering = ["-convocation_year"]
        constraints = [
            models.UniqueConstraint(
                fields=["policy_version", "convocation_year"],
                name="spacs_award_cycle_unique_year",
            )
        ]

    def __str__(self) -> str:
        return f"{self.policy_version.catalogue_entry.title} ({self.convocation_year}) - {self.status}"


class AwardCandidate(TimeStampedModel, UserScopedModel):
    """A candidate in the pool for an award cycle."""

    award_cycle = models.ForeignKey(
        AwardCycle, on_delete=models.CASCADE, related_name="candidates"
    )
    source_method = models.CharField(
        max_length=30,
        choices=[
            ("system_pool", "System Generated"),
            ("application", "Student Application"),
            ("nomination", "Faculty Nomination"),
        ],
    )
    academic_snapshot = models.JSONField(
        default=dict, blank=True,
        help_text="Student CPI, transcript summary, and credits frozen for evaluation"
    )
    nomination_data = models.JSONField(
        default=dict, blank=True,
        help_text="Nominator details and citation where applicable"
    )
    is_eligible = models.BooleanField(default=True)
    ineligibility_notes = models.CharField(max_length=300, blank=True)

    # Committee Evaluation (UC-SPACS-018)
    evaluation_score = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    committee_recommendation = models.CharField(
        max_length=20, blank=True,
        choices=[
            ("shortlisted", "Shortlisted"),
            ("recommended", "Recommended for Award"),
            ("rejected", "Not Recommended"),
        ],
    )
    committee_remarks = models.TextField(blank=True)
    is_final_winner = models.BooleanField(default=False)

    class Meta:
        db_table = "spacs_award_candidate"
        ordering = ["-is_final_winner", "-evaluation_score", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["award_cycle", "user_id"],
                name="spacs_candidate_unique_per_cycle",
            )
        ]

    def __str__(self) -> str:
        return f"Candidate u{self.user_id} in cycle #{self.award_cycle_id}"


class AwardCycleTransition(models.Model):
    """Append-only audit of award cycle state transitions."""

    award_cycle = models.ForeignKey(
        AwardCycle, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role_label = models.CharField(max_length=80)
    reason = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "spacs_award_cycle_transition"
        ordering = ["at"]

    def __str__(self) -> str:
        return f"award cycle#{self.award_cycle_id} {self.from_status} -> {self.to_status} at {self.at}"
