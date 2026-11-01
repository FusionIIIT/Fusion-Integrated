"""Employee service record models (BR-HR-004, BR-HR-005, BR-HR-006)."""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.hreis.domain.leave import DEFAULT_LEAVE_QUOTAS


class EmployeeServiceRecord(TimeStampedModel, UserScopedModel):
    """Centralized service record for faculty and staff.

    Only HR Administrators may create or modify (BR-HR-005).
    Employees have read-only access to their own record (BR-HR-003).
    """

    user_id = models.IntegerField(unique=True, db_index=True)
    employee_id = models.CharField(max_length=64, blank=True, db_index=True)
    department = models.CharField(max_length=128)
    designation = models.CharField(max_length=128)
    category = models.CharField(
        max_length=32,
        choices=[("faculty", "Faculty"), ("staff", "Staff")],
        default="faculty",
    )
    appointment_date = models.DateField(null=True, blank=True)
    retirement_date = models.DateField(null=True, blank=True)
    retirement_status = models.CharField(
        max_length=32,
        choices=[("active", "Active"), ("retired", "Retired"), ("resigned", "Resigned")],
        default="active",
    )
    service_history = models.JSONField(default=list, blank=True)
    leave_balances = models.JSONField(default=dict, blank=True)
    cpda_balance = models.DecimalField(max_digits=12, decimal_places=2, default=300000.00)
    ltc_eligible_block = models.CharField(max_length=32, default="2026-2029", blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "hreis_employee_service_record"
        verbose_name = "Employee Service Record"
        verbose_name_plural = "Employee Service Records"

    def save(self, *args, **kwargs):
        if not self.leave_balances:
            self.leave_balances = dict(DEFAULT_LEAVE_QUOTAS)
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"ServiceRecord(user_id={self.user_id}, emp_id={self.employee_id}, dept={self.department})"
