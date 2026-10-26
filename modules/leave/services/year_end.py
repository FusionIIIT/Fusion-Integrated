"""Year-end leave entitlement processing service (BR-EL-002..009, EL-UC-020, CFR-EL-028).

Enforces:
- Lapse of unused CL, RH, SCL (BR-EL-002, BR-EL-003, BR-EL-004)
- 2:1 conversion of unused faculty VL to EL, including fractional conversion (BR-EL-007, BR-EL-008)
- Carry-forward of unused EL and COL according to policy (BR-EL-005, BR-EL-009)
- Idempotent execution protected by row-level locking (select_for_update)
- Strict append-only ledger entry audit trail (LeaveLedgerEntry)
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction

from modules.leave.domain.entitlement import (
    CATEGORIES_THAT_CARRY_FORWARD,
    CATEGORIES_THAT_LAPSE,
    calculate_vl_to_el_conversion,
)
from modules.leave.models import LeaveBalance, LeaveLedgerEntry, LeaveType

logger = logging.getLogger(__name__)


@dataclass
class EmployeeYearEndSummary:
    user_id: int
    lapsed: dict[str, Decimal] = field(default_factory=dict)
    converted: dict[str, Decimal] = field(default_factory=dict)
    carried_forward: dict[str, Decimal] = field(default_factory=dict)
    exceptions: list[str] = field(default_factory=list)
    skipped: bool = False


@dataclass
class YearEndReport:
    from_year: int
    to_year: int
    processed_users: int = 0
    skipped_users: int = 0
    total_lapsed: dict[str, Decimal] = field(default_factory=dict)
    total_converted: dict[str, Decimal] = field(default_factory=dict)
    total_carried_forward: dict[str, Decimal] = field(default_factory=dict)
    user_summaries: dict[int, EmployeeYearEndSummary] = field(default_factory=dict)
    exceptions: list[str] = field(default_factory=list)


def process_year_end(
    from_year: int,
    to_year: int | None = None,
    user_ids: Sequence[int] | None = None,
    ceilings: dict[str, Decimal] | None = None,
    performed_by_user_id: int | None = None,
    dry_run: bool = False,
) -> YearEndReport:
    """Execute year-end leave balance processing for the specified leave year.

    Args:
        from_year: The year being closed.
        to_year: The new leave year receiving carry-forward balances and conversions.
                 Defaults to from_year + 1.
        user_ids: Optional sequence of user IDs to process. If omitted, all users
                  with balance rows in from_year are processed.
        ceilings: Optional mapping of leave category code to maximum carry-forward ceiling
                  (e.g. {"EL": Decimal("300.0")}). If omitted, full balance carries forward.
        performed_by_user_id: Optional ID of the user executing the process.
        dry_run: If True, executes the entire run inside a rolled-back transaction.

    Returns:
        YearEndReport with counts, adjustments, and exceptions.
    """
    if to_year is None:
        to_year = from_year + 1

    report = YearEndReport(from_year=from_year, to_year=to_year)

    if dry_run:
        with transaction.atomic():
            _execute_year_end(
                from_year=from_year,
                to_year=to_year,
                user_ids=user_ids,
                ceilings=ceilings,
                performed_by_user_id=performed_by_user_id,
                report=report,
            )
            transaction.set_rollback(True)
        return report

    _execute_year_end(
        from_year=from_year,
        to_year=to_year,
        user_ids=user_ids,
        ceilings=ceilings,
        performed_by_user_id=performed_by_user_id,
        report=report,
    )
    return report


def _execute_year_end(
    from_year: int,
    to_year: int,
    user_ids: Sequence[int] | None,
    ceilings: dict[str, Decimal] | None,
    performed_by_user_id: int | None,
    report: YearEndReport,
) -> None:
    # Resolve target user IDs
    if user_ids is not None:
        target_ids = sorted({int(i) for i in user_ids if i is not None})
    else:
        target_ids = sorted(
            LeaveBalance.objects.filter(year=from_year).values_list("user_id", flat=True).distinct()
        )

    if not target_ids:
        return

    # Pre-fetch and validate leave types
    leave_types_by_code: dict[str, LeaveType] = {
        lt.code.upper(): lt for lt in LeaveType.objects.all()
    }

    for uid in target_ids:
        try:
            with transaction.atomic():
                summary = _process_single_employee_year_end(
                    user_id=uid,
                    from_year=from_year,
                    to_year=to_year,
                    leave_types_by_code=leave_types_by_code,
                    ceilings=ceilings,
                    performed_by_user_id=performed_by_user_id,
                )
                report.user_summaries[uid] = summary
                if summary.skipped:
                    report.skipped_users += 1
                else:
                    report.processed_users += 1
                    # Accumulate totals
                    for k, v in summary.lapsed.items():
                        curr_l = report.total_lapsed.get(k, Decimal("0.0"))
                        report.total_lapsed[k] = curr_l + v
                    for k, v in summary.converted.items():
                        curr_v = report.total_converted.get(k, Decimal("0.0"))
                        report.total_converted[k] = curr_v + v
                    for k, v in summary.carried_forward.items():
                        report.total_carried_forward[k] = (
                            report.total_carried_forward.get(k, Decimal("0.0")) + v
                        )
                if summary.exceptions:
                    report.exceptions.extend(summary.exceptions)
        except Exception as exc:
            msg = f"Failed to process user {uid} for year {from_year}: {exc}"
            logger.exception(msg)
            report.exceptions.append(msg)


def _process_single_employee_year_end(
    user_id: int,
    from_year: int,
    to_year: int,
    leave_types_by_code: dict[str, LeaveType],
    ceilings: dict[str, Decimal] | None,
    performed_by_user_id: int | None,
) -> EmployeeYearEndSummary:
    """Process year-end rules for a single employee under row-level lock."""
    summary = EmployeeYearEndSummary(user_id=user_id)

    # 1. Lock all from_year balances for this user to guarantee concurrency isolation
    balances = list(
        LeaveBalance.objects.select_for_update()
        .filter(user_id=user_id, year=from_year)
        .select_related("leave_type")
    )

    if not balances:
        summary.exceptions.append(f"No balances found for user {user_id} in year {from_year}")
        return summary

    # 2. Check for idempotency: if any balance already has a year-end entry for from_year, skip
    balance_ids = [b.id for b in balances]
    already_processed = LeaveLedgerEntry.objects.filter(
        balance_id__in=balance_ids,
        reference_type="year_end",
        reference_id=from_year,
    ).exists()

    if already_processed:
        summary.skipped = True
        return summary

    balance_map = {b.leave_type.code.upper(): b for b in balances if b.leave_type}

    # 3. Process categories that lapse (CL, RH, SCL, or lapses_at_year_end=True)
    for code, b in balance_map.items():
        if code in CATEGORIES_THAT_LAPSE or getattr(b.leave_type, "lapses_at_year_end", False):
            # Do not lapse VL here; VL undergoes conversion
            if code == "VL":
                continue
            unused = b.available_days
            if unused > Decimal("0.0"):
                b.available_days = Decimal("0.0")
                b.save(update_fields=["available_days", "updated_at"])
                LeaveLedgerEntry.objects.create(
                    balance=b,
                    entry_type="lapse",
                    amount=-unused,
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=f"Year-end {from_year} lapse of {unused} unused {code}",
                    performed_by_user_id=performed_by_user_id,
                )
                summary.lapsed[code] = unused
            else:
                # Audit marker for 0.0 balance
                LeaveLedgerEntry.objects.create(
                    balance=b,
                    entry_type="lapse",
                    amount=Decimal("0.0"),
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=f"Year-end {from_year} lapse: 0.0 unused {code}",
                    performed_by_user_id=performed_by_user_id,
                )
                summary.lapsed[code] = Decimal("0.0")

    # 4. Process Faculty VL to EL conversion (BR-EL-007, BR-EL-008)
    if "VL" in balance_map:
        vl_b = balance_map["VL"]
        unused_vl = vl_b.available_days
        el_type = leave_types_by_code.get("EL")
        if not el_type:
            summary.exceptions.append("LeaveType EL missing; cannot convert VL.")
        else:
            if unused_vl > Decimal("0.0"):
                converted_el = calculate_vl_to_el_conversion(unused_vl)
                # Deduct from from_year VL
                vl_b.available_days = Decimal("0.0")
                vl_b.save(update_fields=["available_days", "updated_at"])
                LeaveLedgerEntry.objects.create(
                    balance=vl_b,
                    entry_type="conversion",
                    amount=-unused_vl,
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=(
                        f"Year-end {from_year} VL conversion: {unused_vl} VL -> {converted_el} EL"
                    ),
                    performed_by_user_id=performed_by_user_id,
                )

                # Credit to to_year EL balance
                el_to_year, _ = LeaveBalance.objects.select_for_update().get_or_create(
                    user_id=user_id,
                    leave_type=el_type,
                    year=to_year,
                    defaults={
                        "credited_days": Decimal("0.0"),
                        "available_days": Decimal("0.0"),
                        "used_days": Decimal("0.0"),
                    },
                )
                el_to_year.available_days += converted_el
                el_to_year.credited_days += converted_el
                el_to_year.save(update_fields=["available_days", "credited_days", "updated_at"])
                LeaveLedgerEntry.objects.create(
                    balance=el_to_year,
                    entry_type="conversion",
                    amount=converted_el,
                    balance_after=el_to_year.available_days,
                    reference_type="year_end",
                    reference_id=from_year,
                    description=(f"Year-end {from_year} converted EL credit from {unused_vl} VL"),
                    performed_by_user_id=performed_by_user_id,
                )
                summary.converted["VL_TO_EL"] = converted_el
            else:
                LeaveLedgerEntry.objects.create(
                    balance=vl_b,
                    entry_type="conversion",
                    amount=Decimal("0.0"),
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=f"Year-end {from_year} VL conversion: 0.0 unused VL",
                    performed_by_user_id=performed_by_user_id,
                )
                summary.converted["VL_TO_EL"] = Decimal("0.0")

    # 5. Process categories that carry forward (EL, COL, or carries_forward=True)
    for code, b in balance_map.items():
        if code in CATEGORIES_THAT_CARRY_FORWARD or getattr(b.leave_type, "carries_forward", False):
            unused = b.available_days
            ceiling = ceilings.get(code) if ceilings else None

            if unused > Decimal("0.0"):
                if ceiling is not None and unused > ceiling:
                    carry_amount = ceiling
                    excess_lapsed = unused - ceiling
                else:
                    carry_amount = unused
                    excess_lapsed = Decimal("0.0")

                # Deduct from from_year balance (transferring forward)
                b.available_days = Decimal("0.0")
                b.save(update_fields=["available_days", "updated_at"])
                desc = f"Year-end {from_year} carry forward to {to_year} ({carry_amount} days"
                if excess_lapsed > Decimal("0.0"):
                    desc += f", {excess_lapsed} lapsed above ceiling of {ceiling})"
                else:
                    desc += ")"
                LeaveLedgerEntry.objects.create(
                    balance=b,
                    entry_type="carry_forward",
                    amount=-unused,
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=desc,
                    performed_by_user_id=performed_by_user_id,
                )

                # Credit into to_year balance
                to_balance, _ = LeaveBalance.objects.select_for_update().get_or_create(
                    user_id=user_id,
                    leave_type=b.leave_type,
                    year=to_year,
                    defaults={
                        "credited_days": Decimal("0.0"),
                        "available_days": Decimal("0.0"),
                        "used_days": Decimal("0.0"),
                    },
                )
                to_balance.available_days += carry_amount
                to_balance.credited_days += carry_amount
                to_balance.save(update_fields=["available_days", "credited_days", "updated_at"])
                LeaveLedgerEntry.objects.create(
                    balance=to_balance,
                    entry_type="carry_forward",
                    amount=carry_amount,
                    balance_after=to_balance.available_days,
                    reference_type="year_end",
                    reference_id=from_year,
                    description=f"Year-end carry forward from {from_year} ({carry_amount} days)",
                    performed_by_user_id=performed_by_user_id,
                )
                summary.carried_forward[code] = carry_amount
            else:
                LeaveLedgerEntry.objects.create(
                    balance=b,
                    entry_type="carry_forward",
                    amount=Decimal("0.0"),
                    balance_after=Decimal("0.0"),
                    reference_type="year_end",
                    reference_id=from_year,
                    description=f"Year-end {from_year} carry forward: 0.0 unused {code}",
                    performed_by_user_id=performed_by_user_id,
                )
                summary.carried_forward[code] = Decimal("0.0")

    return summary
