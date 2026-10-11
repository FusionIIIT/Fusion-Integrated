"""Leave policy, category rules, and authority hierarchy."""

from decimal import Decimal

from django.db import models


class Policy(models.Model):
    version = models.CharField(max_length=32, unique=True)
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    published = models.BooleanField(default=False)
    note = models.TextField(blank=True)

    vl_to_el_ratio = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("2.0"))
    vl_to_el_rounding = models.CharField(max_length=16, default="half_up")
    early_return_tail = models.BooleanField(default=True)
    max_backdate_days = models.IntegerField(default=30)

    class Meta:
        db_table = "leave_policy"

    def __str__(self) -> str:
        return f"Policy {self.version} ({'published' if self.published else 'draft'})"


class CategoryRule(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name="category_rules")
    category = models.CharField(max_length=8)
    annual_credit = models.DecimalField(max_digits=5, decimal_places=2)
    carries_forward = models.BooleanField(default=False)
    carry_forward_cap = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    applies_to_faculty = models.BooleanField(default=True)
    requires_evidence = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_category_rule"
        constraints = [
            models.UniqueConstraint(
                fields=["policy", "category", "applies_to_faculty"], name="leave_cat_rule_unique"
            ),
        ]

    def __str__(self) -> str:
        return f"Rule {self.category} (Policy {self.policy.version})"


class AuthorityRule(models.Model):
    policy = models.ForeignKey(Policy, on_delete=models.CASCADE, related_name="authority_rules")
    category = models.CharField(max_length=8, blank=True)
    unit = models.CharField(max_length=128, blank=True)
    designation = models.CharField(max_length=128, blank=True)
    applies_to_faculty = models.BooleanField(default=True)
    establishment_step = models.BooleanField(default=False)
    sanctioning_designation = models.CharField(max_length=128)
    self_sanction = models.BooleanField(default=False)
    specificity = models.IntegerField(default=0)

    class Meta:
        db_table = "leave_authority_rule"

    def __str__(self) -> str:
        return f"AuthRule {self.category} -> {self.sanctioning_designation}"
