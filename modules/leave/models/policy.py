"""Policy, hierarchy and SLA configuration (blueprint Step 3.2).

Two of the three tables are interim placeholders. The specification says
leave-policy parameters use the *current configured values with no
draft/publish/effective-version lifecycle* (BR-EL-030, CFR-EL-024); the
platform convention says admin configuration is *effective-dated and never
edited* (``new-module-prompt.md:244-248``). The two are opposed. Blueprint
§3.8 #1 is UNRESOLVED, so the lifecycle field set is deliberately omitted here
and these shapes must not be treated as final.

No policy or SLA rows are seeded: doing so would choose behaviour the
specification has not settled.
"""
from django.db import models

from core.db.mixins import TimeStampedModel

#: The six leave categories of BR-EL-001. Shared with the request and ledger
#: tables so the vocabulary lives in one place.
LEAVE_TYPE_CHOICES = [
    ("CL", "Casual Leave"),
    ("RH", "Restricted Holiday"),
    ("SCL", "Special Casual Leave"),
    ("EL", "Earned Leave"),
    ("COL", "Commuted Leave"),
    ("VL", "Vacation Leave"),
]


class LeaveTypePolicy(TimeStampedModel):
    """Per-category policy parameters — PROVISIONAL / BLOCKED (#1).

    Interim placeholder: only the content fields the blueprint names are here.
    The lifecycle choice (``is_active`` vs ``effective_from``/``effective_to``/
    ``version``) is the open question and is intentionally not made. In
    particular ``code`` is not declared unique, because uniqueness presupposes
    the un-versioned "current-only" shape that is still under dispute.
    """

    code = models.CharField(max_length=8, choices=LEAVE_TYPE_CHOICES, db_index=True)
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2,
                                             null=True, blank=True)
    carry_forward = models.BooleanField(null=True, blank=True)
    #: BR-EL-007's 2:1 VL→EL ratio, where the category converts.
    conversion_ratio = models.DecimalField(max_digits=6, decimal_places=2,
                                           null=True, blank=True)
    #: Free text, deliberately un-enumerated: BR-EL-005/006 speak of
    #: "non-faculty"/"faculty" while the platform's kinds are faculty/staff, and
    #: that split is unsettled (#7). No vocabulary is imposed here.
    applies_to_kind = models.CharField(max_length=60, blank=True)

    class Meta:
        db_table = "leave_type_policy"
        verbose_name_plural = "leave type policies"

    def __str__(self) -> str:
        return self.code


class HierarchyStep(TimeStampedModel):
    """Ordered approval steps — PROVISIONAL / BLOCKED (#1, #4).

    ``required_designation`` holds a ``globals_designation`` spelling, but
    whether the WF's authority names exist as designation rows is unverified
    (blueprint §3.8 #4), and the source of the hierarchy is unresolved, so no
    rows are seeded and no order is asserted.
    """

    leave_type = models.CharField(max_length=8, blank=True)
    step_order = models.PositiveSmallIntegerField()
    required_designation = models.CharField(max_length=120, blank=True)
    #: The Establishment step is optional where configured (BR-EL-019).
    optional_flag = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_hierarchy_step"
        ordering = ["leave_type", "step_order"]

    def __str__(self) -> str:
        return f"{self.leave_type or '*'} step {self.step_order}"


class SlaThreshold(TimeStampedModel):
    """Configurable SLA thresholds — EXPLICIT (CFR-EL-029, BR-EL-038).

    Thresholds are configured, not coded: reminders and escalations fire only
    while a task is pending (BR-EL-032/033).
    """

    task_class = models.CharField(max_length=60, db_index=True)
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    escalation_action = models.CharField(max_length=120, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "leave_sla_threshold"

    def __str__(self) -> str:
        return self.task_class
