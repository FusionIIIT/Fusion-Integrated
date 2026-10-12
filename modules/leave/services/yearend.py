"""The leave-year boundary sweep (PS §3, BR-EL-002…009).

Lapse what does not survive (CL/RH/SCL), convert faculty VL into EL at the
policy ratio, carry EL and COL forward — once per year, proven by a
`LeaveYearRun` row so a second sweep is a no-op rather than a double debit.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.directory import contracts as directory
from modules.leave.domain import year_end as plan_domain
from modules.leave.domain.categories import COL, EL
from modules.leave.models import LeaveBalance, LeaveYearRun
from modules.leave.services import balances as balances_service
from modules.leave.services.policy import current_policy


def run_year_end(year: int) -> dict:
    policy = current_policy()
    with transaction.atomic():
        existing = (LeaveYearRun.objects.select_for_update()
                    .filter(year=year).first())
        if existing is not None:
            return {"already_run": True, **(existing.report or {})}

        # Everyone gets their expiring year materialised first, or a faculty
        # member who never touched VL would silently lose the conversion.
        is_faculty: dict[int, bool] = {}
        for person in directory.get_employees():
            is_faculty[person.user_id] = person.kind == "faculty"
            balances_service.ensure_year(person.user_id, year,
                                         kind=person.kind, credit=False)

        snapshot = [
            (user_id, category, carried + credited + adjusted - used)
            for user_id, category, carried, credited, adjusted, used
            in LeaveBalance.objects.filter(year=year).values_list(
                "user_id", "category", "carried_forward", "credited",
                "adjusted", "used")
        ]
        plan = plan_domain.plan_year_end(
            year=year, balances=snapshot, is_faculty=is_faculty,
            vl_to_el_numerator=policy.vl_to_el_numerator,
            vl_to_el_denominator=policy.vl_to_el_denominator,
            carry_forward_enabled={EL: policy.el_carry_forward,
                                   COL: policy.col_carry_forward},
        )

        posted = 0
        for entry in plan.entries:
            balances_service.post(entry.user_id, entry.category, entry.year,
                                  entry.kind, entry.days,
                                  note=f"year-end {year}", credit=False)
            posted += 1

        report = {"entries": posted, "balances": len(snapshot),
                  "exceptions": list(plan.exceptions)}
        try:
            LeaveYearRun.objects.create(year=year, report=report)
        except IntegrityError as exc:
            # A concurrent sweep won the marker; this one's effects roll back
            # with the transaction, leaving exactly one processed boundary.
            raise ConflictError(
                f"Leave year {year} has already been processed.",
                code="already_run") from exc
        return {"already_run": False, **report}
