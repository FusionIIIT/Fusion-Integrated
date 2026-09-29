"""Leave policy, effective-dated."""
from django.db import models

from core.db.mixins import TimeStampedModel
from modules.leave.domain.categories import Category
from modules.leave.domain.counting import TailPolicy
from modules.leave.domain.entitlement import ConversionRounding

CATEGORY_CHOICES = [(c.value, c.value) for c in Category]


class LeavePolicy(TimeStampedModel):
    """One published set of leave settings, in force from a date."""

    version = models.CharField(max_length=32, unique=True)
    effective_from = models.DateField(db_index=True)
    effective_to = models.DateField(null=True, blank=True)
    published = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    # BR-EL-007. How many vacation days buy one earned leave day.
    vl_to_el_ratio = models.DecimalField(max_digits=5, decimal_places=2, default=2)
    vl_to_el_rounding = models.CharField(
        max_length=16,
        choices=[(r.value, r.value) for r in ConversionRounding],
        default=ConversionRounding.EXACT_HALF.value,
    )
    #: How far back an application may reach.
    max_backdate_days = models.PositiveIntegerField(default=0)

    # BR-EL-028. Whether a closed tail is restored when duty resumes early.
    early_return_tail = models.CharField(
        max_length=32,
        choices=[(t.value, t.value) for t in TailPolicy],
        default=TailPolicy.TRIM_TO_LAST_WORKING_DAY.value,
    )

    class Meta:
        db_table = "leave_policy"
        ordering = ["-effective_from"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(effective_to__isnull=True)
                | models.Q(effective_to__gt=models.F("effective_from")),
                name="leave_policy_period_valid",
            ),
            models.CheckConstraint(
                condition=models.Q(vl_to_el_ratio__gt=0),
                name="leave_policy_ratio_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["published", "effective_from"], name="leave_policy_lookup_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.version} from {self.effective_from}"


class CategoryRule(TimeStampedModel):
    """One category's settings under one policy version."""

    policy = models.ForeignKey(LeavePolicy, on_delete=models.CASCADE, related_name="rules")
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    annual_credit = models.DecimalField(max_digits=6, decimal_places=2)
    carries_forward = models.BooleanField(default=False)
    carry_forward_cap = models.DecimalField(
        max_digits=6, decimal_places=2, null=True, blank=True
    )
    #: Faculty and non-faculty are credited differently. Null applies to both.
    applies_to_faculty = models.BooleanField(null=True, blank=True)
    requires_evidence = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_category_rule"
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "category", "applies_to_faculty"],
                name="leave_rule_unique_per_policy",
            ),
            models.CheckConstraint(
                condition=models.Q(annual_credit__gte=0),
                name="leave_rule_credit_not_negative",
            ),
            models.CheckConstraint(
                condition=models.Q(carry_forward_cap__isnull=True)
                | models.Q(carry_forward_cap__gte=0),
                name="leave_rule_cap_not_negative",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.category} under {self.policy_id}"
