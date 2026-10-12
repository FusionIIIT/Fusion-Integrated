"""Who reviews, routes and sanctions: org units, authority assignments, SLAs.

The routing hierarchy (BR-EL-016…020) is configured here rather than read
from the directory: the directory publishes who people are, not which desk
reviews a leave file. `user_id` fields are plain integers — the IAM owns
identity.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class OrganizationalUnit(TimeStampedModel):
    """A department / section whose head is the Unit Head for its staff.

    `code` matches the `department` string on directory users so a request
    can find its unit without a cross-boundary foreign key.
    """

    DEPARTMENT = "department"
    SECTION = "section"
    OFFICE = "office"
    KIND = [(DEPARTMENT, "Department"), (SECTION, "Section"),
            (OFFICE, "Office")]

    code = models.CharField(max_length=80, unique=True)
    name = models.CharField(max_length=160)
    kind = models.CharField(max_length=12, choices=KIND, default=DEPARTMENT)
    head_user_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        db_table = "leave_organizational_unit"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class AuthorityAssignment(TimeStampedModel):
    """Which user currently holds a sanctioning desk.

    The establishment step (role_code=establishment) may be assigned per org
    unit or institute-wide (org_unit is null). The final authority roles are
    checked in order dean → registrar → director, org-specific before
    institute-wide, and the first whose `categories` include the request's
    category wins (BR-EL-018/019, config-driven hierarchy).
    """

    ESTABLISHMENT = "establishment"
    DEAN = "dean"
    REGISTRAR = "registrar"
    DIRECTOR = "director"
    ROLE = [(ESTABLISHMENT, "Establishment Section"), (DEAN, "Dean"),
            (REGISTRAR, "Registrar"), (DIRECTOR, "Director")]

    role_code = models.CharField(max_length=20, choices=ROLE)
    user_id = models.IntegerField(db_index=True)
    org_unit = models.ForeignKey(OrganizationalUnit, null=True, blank=True,
                                 on_delete=models.CASCADE,
                                 related_name="authorities")
    #: Categories this desk sanctions; empty means every category.
    categories = models.JSONField(default=list, blank=True)

    class Meta:
        db_table = "leave_authority_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["role_code", "org_unit"],
                name="leave_authority_role_unit_unique"),
        ]

    def __str__(self) -> str:
        return f"{self.get_role_code_display()} → {self.user_id}"


class SlaThreshold(TimeStampedModel):
    """How long a task sits before the reminder, and before escalation
    (BR-EL-032…034). One row per task class."""

    SUBSTITUTE_RESPONSE = "substitute_response"
    UNIT_HEAD_REVIEW = "unit_head_review"
    ESTABLISHMENT_ROUTING = "establishment_routing"
    FINAL_SANCTION = "final_sanction"
    DIRECTOR_SANCTION = "director_sanction"
    RESUMPTION_REVIEW = "resumption_review"
    TASK_CLASS = [
        (SUBSTITUTE_RESPONSE, "Substitute response"),
        (UNIT_HEAD_REVIEW, "Unit Head review"),
        (ESTABLISHMENT_ROUTING, "Establishment routing"),
        (FINAL_SANCTION, "Final sanction"),
        (DIRECTOR_SANCTION, "Director self-sanction"),
        (RESUMPTION_REVIEW, "Resumption review"),
    ]

    task_class = models.CharField(max_length=32, choices=TASK_CLASS,
                                  unique=True)
    reminder_hours = models.PositiveIntegerField(null=True, blank=True)
    escalation_hours = models.PositiveIntegerField(null=True, blank=True)
    #: Whom the escalation notifies; null falls back to the task holder.
    escalation_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_sla_threshold"

    def __str__(self) -> str:
        return self.task_class
