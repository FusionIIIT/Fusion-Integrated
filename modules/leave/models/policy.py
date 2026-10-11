"""Leave policy and academic vacation models.

BR-EL-030: Current configured leave policy parameters.
BR-EL-006: Academic vacation periods.
"""
from decimal import Decimal

from django.db import models

from core.db.mixins import TimeStampedModel


class LeavePolicy(TimeStampedModel):
    cl_entitlement = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("8.0"))
    rh_entitlement = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("2.0"))
    scl_entitlement = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("15.0"))
    faculty_vl_entitlement = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("60.0"))
    nonfaculty_el_credit = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("30.0"))
    col_entitlement = models.DecimalField(max_digits=4, decimal_places=1, default=Decimal("20.0"))
    vl_to_el_ratio = models.DecimalField(max_digits=4, decimal_places=2, default=Decimal("2.00"))
    max_el_carry_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("300.0"))
    max_col_carry_forward = models.DecimalField(max_digits=5, decimal_places=1, default=Decimal("240.0"))
    establishment_step_enabled = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Leave policies"


class VacationPeriod(TimeStampedModel):
    name = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    academic_year = models.CharField(max_length=20, default="2026-27")

    class Meta:
        ordering = ["start_date"]
