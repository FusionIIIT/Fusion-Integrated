"""Upsert employment and Academic Calendar projections from their owners."""
from django.db import transaction
from django.utils import timezone

from modules.leave.contracts import (
    EmploymentProjection, ProjectionSyncResult, VacationPeriodProjection,
)
from modules.leave.models import EmployeeProfile, VacationPeriod


@transaction.atomic
def sync_projections(*, employments=(), vacation_periods=()) -> ProjectionSyncResult:
    """Apply a batch from HR/identity and Academic Calendar contracts."""
    employee_count = vacation_count = 0
    now = timezone.now()
    for row in employments:
        if not isinstance(row, EmploymentProjection):
            raise TypeError("employments must contain EmploymentProjection values")
        if row.kind not in {EmployeeProfile.Kind.FACULTY, EmployeeProfile.Kind.STAFF}:
            raise ValueError(f"Unsupported ELM employee kind for user {row.user_id}")
        _, created = EmployeeProfile.objects.update_or_create(
            user_id=row.user_id,
            defaults={"kind": row.kind, "designation": row.designation,
                      "unit_code": row.unit_code, "unit_head_user_id": row.unit_head_user_id,
                      "is_director": row.is_director, "active": row.active,
                      "synced_at": now},
        )
        employee_count += 1
    for row in vacation_periods:
        if not isinstance(row, VacationPeriodProjection):
            raise TypeError("vacation_periods must contain VacationPeriodProjection values")
        if row.end_date < row.start_date:
            raise ValueError(f"Invalid Academic Calendar interval {row.external_id}")
        VacationPeriod.objects.update_or_create(
            external_id=row.external_id,
            defaults={"label": row.label, "start_date": row.start_date,
                      "end_date": row.end_date, "academic_year": row.academic_year,
                      "synced_at": now},
        )
        vacation_count += 1
    return ProjectionSyncResult(employee_count, vacation_count)
