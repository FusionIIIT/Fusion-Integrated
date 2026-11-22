"""Current configured policy and the hierarchy it routes through (BR-EL-030, BR-EL-038).

No draft/publish/effective-version lifecycle, because the specification forbids
one for leave-policy parameters (AFR-EL-024.4). Validation and routing read these
rows directly. The holiday/RH calendar is the one effective-dated surface, and
it lives in calendar.py.
"""
from __future__ import annotations

from decimal import Decimal

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain import policy as policy_domain
from modules.leave.domain import routing as routing_domain


class LeavePolicy(TimeStampedModel):
    """The current configured parameters (CFR-EL-024, EL-UC-014)."""
    #: One row, enforced rather than assumed.
    singleton = models.PositiveSmallIntegerField(default=1, unique=True,
                                                  editable=False)

    casual_days = models.DecimalField(max_digits=6, decimal_places=2,
                                      default=policy_domain.DEFAULT_CASUAL_DAYS)
    restricted_holiday_days = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=policy_domain.DEFAULT_RESTRICTED_HOLIDAY_DAYS)
    special_casual_days = models.DecimalField(
        max_digits=6, decimal_places=2,
        default=policy_domain.DEFAULT_SPECIAL_CASUAL_DAYS)
    earned_days = models.DecimalField(max_digits=6, decimal_places=2,
                                      default=policy_domain.DEFAULT_EARNED_DAYS)
    vacation_days = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=policy_domain.DEFAULT_VACATION_DAYS)
    commuted_days = models.DecimalField(max_digits=6, decimal_places=2,
                                        default=policy_domain.DEFAULT_COMMUTED_DAYS)

    vacation_to_earned_ratio = models.DecimalField(
        max_digits=5, decimal_places=2,
        default=policy_domain.DEFAULT_VACATION_TO_EARNED_RATIO)

    earned_carries_forward = models.BooleanField(default=True)
    commuted_carries_forward = models.BooleanField(default=True)
    #: Null means no cap, because the specification states carry-forward but
    #: names no ceiling; an administrator sets one deliberately.
    earned_carry_forward_cap = models.DecimalField(max_digits=6, decimal_places=2,
                                                   null=True, blank=True)
    commuted_carry_forward_cap = models.DecimalField(max_digits=6, decimal_places=2,
                                                    null=True, blank=True)

    year_end_month = models.PositiveSmallIntegerField(
        default=12, validators=[MinValueValidator(1), MaxValueValidator(12)])

    substitute_required_for = models.JSONField(default=list, blank=True)
    establishment_step_enabled = models.BooleanField(default=False)
    category_kinds = models.JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(singleton=1),
                                   name="leave_policy_singleton"),
            models.CheckConstraint(condition=models.Q(year_end_month__gte=1,
                                                      year_end_month__lte=12),
                                   name="leave_policy_year_end_month_valid"),
        ]

    def __str__(self) -> str:
        return "Current leave policy"

    def as_domain(self) -> policy_domain.Policy:
        return policy_domain.Policy(
            casual_days=self.casual_days,
            restricted_holiday_days=self.restricted_holiday_days,
            special_casual_days=self.special_casual_days,
            earned_days=self.earned_days,
            vacation_days=self.vacation_days,
            commuted_days=self.commuted_days,
            vacation_to_earned_ratio=self.vacation_to_earned_ratio,
            earned_carries_forward=self.earned_carries_forward,
            commuted_carries_forward=self.commuted_carries_forward,
            earned_carry_forward_cap=self.earned_carry_forward_cap,
            commuted_carry_forward_cap=self.commuted_carry_forward_cap,
            year_end_month=self.year_end_month,
            substitute_required_for=frozenset(self.substitute_required_for or ()),
            establishment_step_enabled=self.establishment_step_enabled,
            category_kinds={key: frozenset(value)
                            for key, value in (self.category_kinds or {}).items()},
        )


class OrganizationalUnit(TimeStampedModel):
    """A Department, Section or Office, keyed by the directory's department name.

    The identity service already projects a `department` string per person, so
    this holds only what the projection lacks: who heads the unit.
    """
    name = models.CharField(max_length=80, unique=True)
    head_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name


class HierarchyRoute(TimeStampedModel):
    """An ordered chain of processing steps for a category in a unit (BR-EL-018)."""
    name = models.CharField(max_length=120)
    #: Empty means every category; otherwise the single category it governs.
    leave_category = models.CharField(max_length=8, blank=True, default="")
    #: Null means every unit; otherwise the unit this route is specific to.
    org_unit = models.ForeignKey(OrganizationalUnit, on_delete=models.CASCADE,
                                 null=True, blank=True, related_name="routes")
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("leave_category", "name")
        constraints = [
            models.UniqueConstraint(fields=("name", "leave_category", "org_unit"),
                                    name="leave_route_unique"),
        ]

    def __str__(self) -> str:
        return self.name

    def as_domain(self) -> routing_domain.Route:
        steps = tuple(
            routing_domain.RouteStep(
                kind=row.kind, order=row.order, designation=row.designation,
                user_id=row.user_id)
            for row in self.steps.order_by("order", "id")
        )
        return routing_domain.Route(steps=steps)


class HierarchyRouteStep(TimeStampedModel):
    """One step of a route. The designation is configuration, not a hard-coded post."""
    route = models.ForeignKey(HierarchyRoute, on_delete=models.CASCADE,
                              related_name="steps")
    kind = models.CharField(max_length=32,
                            choices=[(k, k) for k in routing_domain.STEP_KINDS])
    order = models.PositiveSmallIntegerField(default=10)
    designation = models.CharField(
        max_length=120, blank=True, default="",
        help_text="Configured designation label for this step.")
    user_id = models.IntegerField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ("order", "id")
        constraints = [
            models.UniqueConstraint(fields=("route", "kind"),
                                    name="leave_route_step_unique_kind"),
        ]

    def __str__(self) -> str:
        return f"{self.route_id}:{self.kind}"


class SlaThreshold(TimeStampedModel):
    """Reminder and escalation thresholds per task kind (BR-EL-038)."""
    task_kind = models.CharField(max_length=48, unique=True)
    reminder_hours = models.PositiveIntegerField(null=True, blank=True)
    escalate_hours = models.PositiveIntegerField(null=True, blank=True)
    #: The higher or responsible authority an escalation notifies (BR-EL-033).
    escalation_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    escalation_designation = models.CharField(max_length=120, blank=True,
                                              default="")
    #: When true, escalation also moves routing/responsibility (XTP-EL-01).
    escalation_changes_routing = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ("task_kind",)

    def __str__(self) -> str:
        return self.task_kind

    def remind_after(self) -> Decimal | None:
        return None if self.reminder_hours is None else Decimal(self.reminder_hours)

    def escalate_after(self) -> Decimal | None:
        return None if self.escalate_hours is None else Decimal(self.escalate_hours)