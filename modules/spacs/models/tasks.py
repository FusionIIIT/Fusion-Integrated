"""Work routing, stage-aware SLA tracking, and task reassignment for SPACS.

Enforces:
- CFR-SPACS-007 / AFR-SPACS-026 (Review SLA Reminder and Escalation)
- CFR-SPACS-018 / AFR-SPACS-052 (Role Reassignment Routing)
- BR-SPACS-013 (Review SLA and Escalation)
- BR-SPACS-022 (Role Reassignment Preserves History)
- UC-SPACS-024 (Issue SLA Reminder / Escalation)
- UC-SPACS-026 (Reassign Pending Role-Based Tasks)
"""
from __future__ import annotations

from django.db import models
from core.db.mixins import TimeStampedModel


class SpacsTask(TimeStampedModel):
    """Represents an active or historical work item assigned to a role or user."""

    TASK_TYPES = [
        ("verification", "Scholarship Verification"),
        ("decision", "Scholarship Decision"),
        ("award_evaluation", "Award Candidate Evaluation"),
    ]
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    # Target References (CheckConstraint enforces exactly one is set)
    application = models.ForeignKey(
        "ScholarshipApplication", null=True, blank=True,
        on_delete=models.CASCADE, related_name="tasks"
    )
    award_cycle = models.ForeignKey(
        "AwardCycle", null=True, blank=True,
        on_delete=models.CASCADE, related_name="tasks"
    )

    task_type = models.CharField(max_length=32, choices=TASK_TYPES, db_index=True)
    assigned_role = models.CharField(max_length=60, db_index=True)  # e.g., "spacs_assistant", "spacs_convener"
    assigned_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default="pending", db_index=True)

    # Immutability: Binds to governing policy version & stores frozen SLA rules at creation
    policy_version = models.ForeignKey(
        "CataloguePolicyVersion", on_delete=models.PROTECT, related_name="tasks"
    )
    sla_snapshot = models.JSONField(
        default=dict,
        help_text="Immutable copy of policy SLA stages and thresholds at task creation time"
    )

    # Deadlines & Stage-Aware Tracking (UC-SPACS-024)
    due_at = models.DateTimeField(null=True, blank=True)
    sla_notified_stages = models.JSONField(
        default=list,
        help_text="Records completed reminder/escalation stages: [{'stage': str, 'sent_at': str}]"
    )

    completed_at = models.DateTimeField(null=True, blank=True)
    completed_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "spacs_task"
        indexes = [
            models.Index(fields=["assigned_role", "status"], name="spacs_task_role_status_idx"),
            models.Index(fields=["status", "due_at"], name="spacs_task_sla_idx"),
        ]
        constraints = [
            # Exactly one target reference
            models.CheckConstraint(
                condition=(
                    (models.Q(application__isnull=False) & models.Q(award_cycle__isnull=True)) |
                    (models.Q(application__isnull=True) & models.Q(award_cycle__isnull=False))
                ),
                name="spacs_task_exactly_one_target",
            ),
            # Prevent duplicate active tasks for the same application stage
            models.UniqueConstraint(
                fields=["application", "task_type"],
                condition=models.Q(status="pending", application__isnull=False),
                name="spacs_task_unique_active_application_stage",
            ),
            # Prevent duplicate active tasks for the same award cycle stage
            models.UniqueConstraint(
                fields=["award_cycle", "task_type"],
                condition=models.Q(status="pending", award_cycle__isnull=False),
                name="spacs_task_unique_active_award_stage",
            ),
        ]

    def __str__(self) -> str:
        target = f"app #{self.application_id}" if self.application_id else f"award #{self.award_cycle_id}"
        return f"Task({self.task_type} for {target} -> {self.assigned_role} [{self.status}])"
