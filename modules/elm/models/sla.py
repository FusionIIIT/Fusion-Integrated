"""Configurable reminder and escalation thresholds for workflow tasks."""

from django.db import models

from core.db.mixins import TimeStampedModel


class SLAConfiguration(TimeStampedModel):
    """One configuration for each actionable workflow task class."""

    TASK_CLASS = [
        ("new_apply", "New leave application routing"),
        ("authorize", "Unit Head authorization"),
        ("finalize", "Sanctioning authority decision"),
        ("cancel", "Approved leave cancellation"),
        ("extend", "Ongoing leave extension"),
    ]

    task_class = models.CharField(max_length=32, choices=TASK_CLASS, db_index=True)
    reminder_hours = models.PositiveSmallIntegerField(
        default=24,
        help_text="Hours after assignment before a reminder is issued.",
    )
    escalation_hours = models.PositiveSmallIntegerField(
        default=72,
        help_text="Hours after assignment before escalation to the responsible authority.",
    )
    escalation_mode = models.CharField(
        max_length=32,
        choices=[
            ("notify", "Notify only"),
            ("reroute", "Reroute routing/responsibility"),
        ],
        default="notify",
    )

    class Meta:
        db_table = "elm_sla_configuration"
        unique_together = [
            ("task_class", "reminder_hours"),
        ]

    def __str__(self) -> str:
        return f"{self.task_class} -> {self.reminder_hours}h/{self.escalation_hours}h"
