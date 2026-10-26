"""Administrator configuration: every save is a new revision; the newest governs (BR-EL-030)."""
from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel

CATEGORY_CHOICES = [("CL", "CL"), ("RH", "RH"), ("SCL", "SCL"), ("EL", "EL"),
                    ("COL", "COL"), ("VL", "VL")]


class PolicyRevision(models.Model):
    weekend_days = models.JSONField(default=list)
    max_backdate_days = models.PositiveSmallIntegerField(default=0)
    note = models.CharField(max_length=300, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_policy_revision"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"policy r{self.pk}"


class CategoryRule(models.Model):
    revision = models.ForeignKey(PolicyRevision, on_delete=models.CASCADE, related_name="rules")
    category = models.CharField(max_length=4, choices=CATEGORY_CHOICES)
    annual_entitlement = models.DecimalField(max_digits=5, decimal_places=1)
    substitute = models.CharField(max_length=10, default="optional")
    evidence_min_days = models.DecimalField(max_digits=5, decimal_places=1, null=True,
                                            blank=True)

    class Meta:
        db_table = "leave_category_rule"
        constraints = [
            models.UniqueConstraint(fields=["revision", "category"],
                                    name="leave_rule_one_per_category"),
            models.CheckConstraint(condition=Q(annual_entitlement__gte=0),
                                   name="leave_rule_entitlement_nonneg"),
        ]

    def __str__(self) -> str:
        return f"r{self.revision_id} {self.category}"


class HierarchyRevision(models.Model):
    note = models.CharField(max_length=300, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_hierarchy_revision"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"hierarchy r{self.pk}"


class OrgUnit(models.Model):
    """Keyed by the department name the IAM projects for each employee."""

    revision = models.ForeignKey(HierarchyRevision, on_delete=models.CASCADE,
                                 related_name="units")
    department = models.CharField(max_length=100)
    unit_head_designation = models.CharField(max_length=155)
    head_leave_designation = models.CharField(max_length=155, blank=True)

    class Meta:
        db_table = "leave_org_unit"
        constraints = [models.UniqueConstraint(fields=["revision", "department"],
                                               name="leave_unit_one_per_department")]

    def __str__(self) -> str:
        return f"{self.department} -> {self.unit_head_designation}"


class SanctionRoute(models.Model):
    revision = models.ForeignKey(HierarchyRevision, on_delete=models.CASCADE,
                                 related_name="routes")
    employee_kind = models.CharField(max_length=10, blank=True)
    category = models.CharField(max_length=4, blank=True)
    department = models.CharField(max_length=100, blank=True)
    applicant_designation = models.CharField(max_length=155, blank=True)
    establishment_designation = models.CharField(max_length=155, blank=True)
    sanction_designation = models.CharField(max_length=155)

    class Meta:
        db_table = "leave_sanction_route"
        constraints = [models.UniqueConstraint(
            fields=["revision", "employee_kind", "category", "department",
                    "applicant_designation"], name="leave_route_unique_match")]

    def __str__(self) -> str:
        return f"route -> {self.sanction_designation}"


class SlaRevision(models.Model):
    note = models.CharField(max_length=300, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_sla_revision"
        ordering = ["-id"]

    def __str__(self) -> str:
        return f"sla r{self.pk}"


class SlaRule(models.Model):
    revision = models.ForeignKey(SlaRevision, on_delete=models.CASCADE, related_name="rules")
    step = models.CharField(max_length=24)
    reminder_hours = models.PositiveIntegerField()
    escalation_hours = models.PositiveIntegerField()
    action = models.CharField(max_length=10, default="notify")
    escalate_to = models.CharField(max_length=155, blank=True)

    class Meta:
        db_table = "leave_sla_rule"
        constraints = [
            models.UniqueConstraint(fields=["revision", "step"], name="leave_sla_one_per_step"),
            models.CheckConstraint(condition=Q(escalation_hours__gt=F("reminder_hours")),
                                   name="leave_sla_escalation_after_reminder"),
        ]

    def __str__(self) -> str:
        return f"r{self.revision_id} {self.step}"


class HolidayCalendar(TimeStampedModel):
    """BR-EL-031: drafts are invisible to validation; publishing supersedes the previous one."""

    DRAFT, PUBLISHED, SUPERSEDED = "draft", "published", "superseded"
    STATUS = [(DRAFT, "Draft"), (PUBLISHED, "Published"), (SUPERSEDED, "Superseded")]

    year = models.PositiveSmallIntegerField()
    version = models.PositiveSmallIntegerField()
    status = models.CharField(max_length=12, choices=STATUS, default=DRAFT)
    created_by_user_id = models.IntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["year", "version"], name="leave_calendar_version"),
            models.UniqueConstraint(fields=["year"], condition=Q(status="published"),
                                    name="leave_calendar_one_published"),
            models.UniqueConstraint(fields=["year"], condition=Q(status="draft"),
                                    name="leave_calendar_one_draft"),
        ]

    def __str__(self) -> str:
        return f"{self.year} v{self.version} {self.status}"


class Holiday(models.Model):
    CLOSED, RESTRICTED = "closed", "restricted"
    KIND = [(CLOSED, "Closed holiday"), (RESTRICTED, "Restricted holiday")]

    calendar = models.ForeignKey(HolidayCalendar, on_delete=models.CASCADE,
                                 related_name="holidays")
    date = models.DateField()
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=12, choices=KIND)

    class Meta:
        db_table = "leave_holiday"
        ordering = ["date"]
        constraints = [models.UniqueConstraint(fields=["calendar", "date"],
                                               name="leave_holiday_one_per_date")]

    def __str__(self) -> str:
        return f"{self.date} {self.name}"


class VacationPeriod(TimeStampedModel):
    """EXT-01: vacation periods as published by the Academic Calendar."""

    label = models.CharField(max_length=120)
    start_date = models.DateField()
    end_date = models.DateField()
    source_reference = models.CharField(max_length=200, blank=True)
    created_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_vacation_period"
        ordering = ["start_date"]
        constraints = [models.CheckConstraint(condition=Q(end_date__gte=F("start_date")),
                                              name="leave_vacation_ordered")]

    def __str__(self) -> str:
        return self.label
