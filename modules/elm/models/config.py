"""ELM configuration: leave types, routing hierarchy, unit heads, SLA, settings.

BR-EL-030: validation and routing read the CURRENT configured values directly;
there is deliberately no draft/publish/effective-version lifecycle for policy
parameters in this baseline.
"""
from __future__ import annotations

from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveTypeConfig(TimeStampedModel):
    """Per-category policy (BR-EL-002..BR-EL-013)."""

    EMPLOYEE_KIND = [("any", "Any employee"), ("faculty", "Faculty only"),
                     ("staff", "Non-faculty only")]

    category = models.CharField(max_length=8, unique=True)     # CL, RH, ...
    label = models.CharField(max_length=80)
    employee_kind = models.CharField(max_length=8, choices=EMPLOYEE_KIND,
                                     default="any")
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2,
                                             default=0)
    carry_forward = models.BooleanField(default=False)
    continuous = models.BooleanField(default=False)
    half_day = models.BooleanField(default=False)
    requires_substitute = models.BooleanField(default=False)
    requires_resumption = models.BooleanField(default=False)
    allows_extension = models.BooleanField(default=False)
    unit_head_final = models.BooleanField(default=False)
    requires_medical_evidence = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_type_config"
        ordering = ["category"]

    def __str__(self) -> str:
        return self.category


class HierarchyConfig(TimeStampedModel):
    """Routing authority per category (BR-EL-018/019).

    A row with an empty `category` is the module default; a category-specific
    row overrides it.
    """

    category = models.CharField(max_length=8, unique=True, blank=True)
    establishment_required = models.BooleanField(default=False)
    final_authority_designation = models.CharField(max_length=80, default="Registrar")

    class Meta:
        db_table = "elm_hierarchy_config"

    def __str__(self) -> str:
        return self.category or "(default)"


class UnitHeadAssignment(TimeStampedModel):
    """Which employee heads a department (BR-EL-016).

    ELM owns this rather than reading it from the directory projection, which
    carries no unit-head field.
    """

    department = models.CharField(max_length=80, unique=True)
    unit_head_user_id = models.IntegerField(db_index=True)

    class Meta:
        db_table = "elm_unit_head_assignment"

    def __str__(self) -> str:
        return f"{self.department} -> u{self.unit_head_user_id}"


class SlaConfig(TimeStampedModel):
    """Reminder and escalation thresholds per task type (BR-EL-032/033/038)."""

    task_type = models.CharField(max_length=24, unique=True)
    reminder_hours = models.PositiveIntegerField(default=48)
    escalation_hours = models.PositiveIntegerField(default=96)
    escalate_to_designation = models.CharField(max_length=80, blank=True)
    change_routing = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_sla_config"
        ordering = ["task_type"]

    def __str__(self) -> str:
        return self.task_type


class ElmSettings(TimeStampedModel):
    """A singleton: current leave year and the year-end boundary."""

    current_year = models.PositiveSmallIntegerField(default=2026)
    year_end_month = models.PositiveSmallIntegerField(default=12)
    year_end_day = models.PositiveSmallIntegerField(default=31)
    sla_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_settings"

    def __str__(self) -> str:
        return f"ELM settings {self.current_year}"

    @classmethod
    def load(cls) -> ElmSettings:
        return cls.objects.first() or cls.objects.create()
