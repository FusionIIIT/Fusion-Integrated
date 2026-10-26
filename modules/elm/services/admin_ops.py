"""Administrative operations: offline leave sync and year-end processing.

Enforces BR-EL-029, BR-EL-037 (Offline sync) and BR-EL-002..009 (Year-end).
"""
from __future__ import annotations

import datetime
from django.db import transaction

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError, PermissionDeniedError
from modules.elm.domain.counting import calculate_chargeable_days
from modules.elm.domain.year_end import CurrentBalanceSnapshot, compute_year_end_for_employee
from modules.elm.models import (
    LeaveApplication,
    LeaveBalance,
    LeaveType,
    OfflineSanctionRecord,
)
from modules.elm.services.audit import record_audit


def record_offline_leave(
    actor,
    employee_id: int,
    leave_type_id: int,
    start_date: datetime.date,
    end_date: datetime.date,
    sanction_order_no: str,
    sanction_order_date: datetime.date,
    sanctioned_by_role: str,
    remarks: str = "",
) -> OfflineSanctionRecord:
    """Record already-sanctioned offline leave (EL-UC-016, BR-EL-029, BR-EL-037).

    Synchronizes records without creating a second approval workflow.
    """
    user_id = getattr(actor, "user_id", None) or getattr(actor, "id", None)

    try:
        leave_type = LeaveType.objects.get(id=leave_type_id, is_active=True)
    except LeaveType.DoesNotExist:
        raise NotFoundError("Leave type not found.", code="not_found")

    days = calculate_chargeable_days(leave_type.code, start_date, end_date)

    with transaction.atomic():
        balance, _ = LeaveBalance.objects.get_or_create(
            employee_id=employee_id,
            leave_type=leave_type,
            year=start_date.year,
            defaults={"allotted": leave_type.max_days_per_year, "used": 0.0},
        )
        balance.used += days
        balance.save(update_fields=["used", "updated_at"])

        # Create approved application record for history integrity
        app = LeaveApplication.objects.create(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days=days,
            reason=f"Offline sanctioned: Order {sanction_order_no}",
            status="APPROVED",
            sanctioning_authority_role=sanctioned_by_role,
            remarks=remarks,
            decided_at=datetime.datetime.combine(sanction_order_date, datetime.time.min),
        )

        offline_rec = OfflineSanctionRecord.objects.create(
            employee_id=employee_id,
            leave_type=leave_type,
            start_date=start_date,
            end_date=end_date,
            days=days,
            sanction_order_no=sanction_order_no,
            sanction_order_date=sanction_order_date,
            sanctioned_by_role=sanctioned_by_role,
            recorded_by_id=user_id,
            remarks=remarks,
        )

        record_audit(
            application=app,
            actor_id=user_id,
            action="OFFLINE_SANCTION_SYNC",
            from_status="DRAFT",
            to_status="APPROVED",
            remarks=f"Offline sanction sync: {sanction_order_no}",
        )

    return offline_rec


def execute_year_end_processing(
    employee_ids: list[int],
    old_year: int,
    new_year: int,
    faculty_user_ids: set[int] | None = None,
) -> dict[str, int]:
    """Execute year-end rollover, lapse, carry-forward, and VL->EL conversion (EL-UC-020)."""
    faculty_set = faculty_user_ids or set()
    processed_count = 0

    with transaction.atomic():
        for emp_id in employee_ids:
            is_faculty = emp_id in faculty_set
            old_balances = list(LeaveBalance.objects.filter(employee_id=emp_id, year=old_year).select_related("leave_type"))
            if not old_balances:
                continue

            snapshots = [
                CurrentBalanceSnapshot(
                    leave_type_code=b.leave_type.code,
                    year=b.year,
                    allotted=float(b.allotted),
                    used=float(b.used),
                )
                for b in old_balances
            ]

            outcomes = compute_year_end_for_employee(
                balances=snapshots,
                is_faculty=is_faculty,
                old_year=old_year,
                new_year=new_year,
            )

            for out in outcomes:
                leave_type = LeaveType.objects.get(code=out.leave_type_code)
                LeaveBalance.objects.update_or_create(
                    employee_id=emp_id,
                    leave_type=leave_type,
                    year=new_year,
                    defaults={
                        "allotted": out.new_allotted,
                        "used": 0.0,
                        "credited_from_vl": out.converted_amount,
                    },
                )

            processed_count += 1

    return {"processed_employees": processed_count}
