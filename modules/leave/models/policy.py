"""Current configured leave policy, hierarchy and SLA thresholds (BR-EL-030, BR-EL-038).

These are current values, not a versioned policy: the synchronized baseline has
no draft/publish lifecycle for leave parameters, so a configuration change
supersedes by editing the row an administrator is looking at.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    """The one effective policy. Seeded, then maintained by an administrator."""

    is_active = models.BooleanField(default=True)
    effective_from = models.DateField(null=True, blank=True)
    #: BR-EL-020: whoever holds this designation self-sanctions their own leave.
    self_sanction_designation = models.CharField(max_length=64, default="Director")
    #: Days per category; a category absent here falls back to the module default.
    entitlements = models.JSONField(default=dict, blank=True)
    #: Categories for which responsibility coverage has to be nominated.
    substitute_required_categories = models.JSONField(default=list, blank=True)
    #: Categories that may be applied for after the start date, in days.
    max_backdate_days = models.PositiveSmallIntegerField(default=0)
    notes = models.CharField(max_length=300, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_policy"
        constraints = [
            models.UniqueConstraint(fields=["is_active"],
                                    condition=models.Q(is_active=True),
                                    name="leave_policy_single_active"),
        ]

    def __str__(self) -> str:
        return f"leave policy (active={self.is_active})"


class LeaveHierarchyStep(TimeStampedModel):
    """One step of the configured processing/sanctioning path (BR-EL-019)."""

    KINDS = [("unit_head", "Unit Head"), ("establishment", "Establishment"),
             ("final_authority", "Final Sanctioning Authority")]

    sequence = models.PositiveSmallIntegerField(default=10)
    kind = models.CharField(max_length=20, choices=KINDS)
    designation = models.CharField(max_length=64)
    #: Empty means the step applies to every leave category.
    categories = models.JSONField(default=list, blank=True)
    is_active = models.BooleanField(default=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_hierarchy_step"
        ordering = ["sequence", "id"]
        constraints = [
            models.UniqueConstraint(fields=["kind", "designation"],
                                    name="leave_hierarchy_step_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.sequence}: {self.kind} ({self.designation})"


class AcademicVacationPeriod(TimeStampedModel):
    """Vacation dates supplied by the institute Academic Calendar (BR-EL-006).

    Stored locally because VL validation needs them on every submission; the
    academic calendar remains the owner of the dates themselves.
    """

    start_date = models.DateField()
    end_date = models.DateField()
    label = models.CharField(max_length=80, blank=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_academic_vacation"
        ordering = ["start_date"]
        constraints = [
            models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")),
                                   name="vacation_period_ordered"),
        ]

    def __str__(self) -> str:
        return f"{self.start_date}..{self.end_date}"


class SlaThreshold(TimeStampedModel):
    """Reminder and escalation hours per actionable task class (BR-EL-038)."""

    TASK_CLASSES = [("substitute_response", "Substitute response"),
                    ("unit_head_review", "Unit Head review"),
                    ("establishment_routing", "Establishment routing"),
                    ("final_sanction", "Final sanction")]

    task_class = models.CharField(max_length=32, choices=TASK_CLASSES, unique=True)
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    #: Empty means the escalation only notifies; a designation makes it re-route.
    escalation_designation = models.CharField(max_length=64, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_sla_threshold"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(escalation_hours__gte=models.F("reminder_hours")),
                name="sla_escalation_after_reminder"),
        ]

    def __str__(self) -> str:
        return f"{self.task_class}: {self.reminder_hours}/{self.escalation_hours}h"
