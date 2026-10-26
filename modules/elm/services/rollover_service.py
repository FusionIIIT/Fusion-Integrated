"""Year-end leave balance rollover service (EL-UC-020 / BR-EL-002 through BR-EL-009)."""
from decimal import Decimal

from django.db import transaction

from modules.directory.models import UserRef
from modules.elm.domain.policy import (
    MAX_EL_CARRY_FORWARD_CAP,
    LeaveCategory,
    compute_year_end_rollover,
)
from modules.elm.models import LeaveBalance, LeaveRolloverRecord, LeaveType


@transaction.atomic
def execute_year_end_rollover(
    target_year: int,
    authorized_user_id: int | None = None,
    max_el_cap: Decimal = MAX_EL_CARRY_FORWARD_CAP,
    executor_user_id: int | None = None,
) -> list[LeaveRolloverRecord]:
    """Execute year-end leave balance rollover for all employees per EL-UC-020.

    - Lapses unused CL (BR-EL-002), RH (BR-EL-003), SCL (BR-EL-004).
    - Converts unused faculty VL to EL at 2:1 with fractional precision (BR-EL-007, 008).
    - Carries forward EL (BR-EL-005) subject to policy cap (default 300 days).
    - Carries forward COL (BR-EL-009) with 20-day annual increment.
    - Strictly transactional and idempotent (guarded against duplicate execution).
    """
    effective_auth_id = (
        authorized_user_id if authorized_user_id is not None else (executor_user_id or 0)
    )
    authorized_user_id = effective_auth_id
    next_year = target_year + 1
    leave_types = {lt.code: lt for lt in LeaveType.objects.filter(is_active=True)}

    # Identify distinct users with balance records for target_year
    distinct_user_ids = list(
        LeaveBalance.objects.filter(year=target_year)
        .values_list("user_id", flat=True)
        .distinct()
    )

    records: list[LeaveRolloverRecord] = []

    for uid in distinct_user_ids:
        # Idempotency check: prevent duplicate rollover for the same employee and year
        if LeaveRolloverRecord.objects.filter(user_id=uid, year=target_year).exists():
            continue

        user_balances = LeaveBalance.objects.filter(user_id=uid, year=target_year).select_related(
            "leave_type"
        )
        bal_map: dict[str, tuple[Decimal, Decimal]] = {}
        for b in user_balances:
            bal_map[b.leave_type.code] = (Decimal(str(b.allocated)), Decimal(str(b.used)))

        # Determine faculty classification
        user_ref = UserRef.objects.filter(user_id=uid).first()
        is_faculty = (
            user_ref.kind == "faculty"
            if user_ref
            else LeaveCategory.VL.value in bal_map
        )

        calc = compute_year_end_rollover(
            user_id=uid,
            year=target_year,
            current_balances=bal_map,
            is_faculty=is_faculty,
            max_el_cap=max_el_cap,
        )

        # Create or update balance records for next_year
        for code, alloc in calc.next_year_balances.items():
            lt = leave_types.get(code)
            if lt:
                LeaveBalance.objects.update_or_create(
                    user_id=uid,
                    leave_type=lt,
                    year=next_year,
                    defaults={
                        "allocated": alloc,
                        "used": Decimal("0.0"),
                        "pending": Decimal("0.0"),
                    },
                )

        # Record audit log for rollover
        rec = LeaveRolloverRecord.objects.create(
            user_id=uid,
            year=target_year,
            cl_lapsed=calc.cl_lapsed,
            rh_lapsed=calc.rh_lapsed,
            scl_lapsed=calc.scl_lapsed,
            vl_converted=calc.vl_converted,
            el_credited_from_vl=calc.el_credited_from_vl,
            el_carried_forward=calc.el_carried_forward,
            col_carried_forward=calc.col_carried_forward,
            details={
                "authorized_by": authorized_user_id,
                "is_faculty": is_faculty,
                "next_year": next_year,
            },
        )
        records.append(rec)

    return records
