"""Current configured policy and hierarchy (BR-EL-030): edited in place, no versions."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain.categories import Category
from modules.leave.domain.workflow import PENDING

CATEGORY_CHOICES = [(c.value, c.value) for c in Category]


class LeavePolicy(TimeStampedModel):
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES, unique=True)
    annual_days = models.DecimalField(max_digits=5, decimal_places=1)
    requires_substitute = models.BooleanField(default=False)
    max_days_per_request = models.DecimalField(max_digits=5, decimal_places=1,
                                               null=True, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_policy"
        constraints = [models.CheckConstraint(condition=models.Q(annual_days__gte=0),
                                              name="leave_policy_days_non_negative")]


class OrgUnit(TimeStampedModel):
    """`name` is the department string the directory carries for an employee."""

    name = models.CharField(max_length=80, unique=True)
    head_user_id = models.IntegerField(null=True, blank=True)
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                               related_name="children")

    class Meta:
        db_table = "leave_org_unit"


class AuthorityRule(TimeStampedModel):
    """BR-EL-019: the most specific matching rule wins; blank fields match anyone."""

    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    unit = models.ForeignKey(OrgUnit, null=True, blank=True, on_delete=models.CASCADE)
    applicant_kind = models.CharField(max_length=10, blank=True)
    sanctioning_user_id = models.IntegerField()
    establishment_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_authority_rule"
        constraints = [models.UniqueConstraint(
            fields=["category", "unit", "applicant_kind"],
            nulls_distinct=False, name="leave_authority_rule_unique")]


class InstituteOffice(TimeStampedModel):
    DIRECTOR = "director"

    code = models.CharField(max_length=20, unique=True, choices=[(DIRECTOR, "Director")])
    user_id = models.IntegerField()

    class Meta:
        db_table = "leave_institute_office"


class SlaPolicy(TimeStampedModel):
    """BR-EL-038, one row per pending state that has an SLA."""

    state = models.CharField(max_length=32, unique=True,
                             choices=[(s.value, s.value) for s in sorted(PENDING)])
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    escalate_to_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_sla_policy"
        constraints = [models.CheckConstraint(
            condition=models.Q(escalation_hours__gt=models.F("reminder_hours")),
            name="leave_sla_escalation_after_reminder")]
