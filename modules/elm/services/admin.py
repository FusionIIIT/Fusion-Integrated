"""Administrative and automated lifecycle services for Employee Leave Management."""
from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Optional

from django.db import transaction

from modules.elm.domain.policy import (
    ANNUAL_ENTITLEMENTS,
    calculate_leave_duration,
    convert_vl_to_el,
)
from modules.elm.models import (
    LeaveAccount,
    LeavePolicyConfig,
    LeaveRequest,
    LeaveStatus,
    LeaveTransaction,
)


@transaction.atomic
def record_offline_leave(
    employee_id: int,
    category: str,
    start_date: datetime.date,
    end_date: datetime.date,
    sanction_reference: str,
    reason: str,
    is_station_leave: bool = False,
    station_address: str = "",
) -> LeaveRequest:
    """Record leave sanctioned through authorized paper/offline route (BR-EL-029)."""
    duration = calculate_leave_duration(category, start_date, end_date)
    year = start_date.year

    account, _ = LeaveAccount.objects.select_for_update().get_or_create(
        employee_id=employee_id, category=category, year=year
    )
    account.used += duration
    account.available -= duration
    account.save(update_fields=["used", "available"])

    req = LeaveRequest.objects.create(
        applicant_id=employee_id,
        category=category,
        start_date=start_date,
        end_date=end_date,
        duration_days=duration,
        reason=f"[Offline Record Ref: {sanction_reference}] {reason}",
        is_station_leave=is_station_leave,
        station_address=station_address,
        status=LeaveStatus.APPROVED,
        sanctioning_authority_remarks=f"Offline Sanction: {sanction_reference}",
    )

    LeaveTransaction.objects.create(
        account=account,
        delta=-duration,
        transaction_type="OFFLINE_SYNC",
        reference_id=sanction_reference,
        idempotency_key=f"offline_{employee_id}_{sanction_reference}",
    )
    return req


@transaction.atomic
def execute_year_end_processing(year: int, employee_ids: list[int]) -> dict:
    """Execute year-end category lapse, VL-to-EL conversion, and carry-forward (BR-EL-037)."""
    next_year = year + 1
    summary = {"lapsed_accounts": 0, "converted_vl": 0, "carried_forward": 0}

    for emp_id in employee_ids:
        # 1. Lapse CL, RH, SCL (BR-EL-002, BR-EL-003, BR-EL-004)
        for cat in ["CL", "RH", "SCL"]:
            acc = LeaveAccount.objects.filter(employee_id=emp_id, category=cat, year=year).first()
            if acc and acc.available > 0:
                LeaveTransaction.objects.create(
                    account=acc,
                    delta=-acc.available,
                    transaction_type="YEAR_END_LAPSE",
                    reference_id=f"lapse_{year}_{cat}",
                )
                acc.available = Decimal("0.0")
                acc.save(update_fields=["available"])
                summary["lapsed_accounts"] += 1

        # 2. Convert unused Faculty VL to EL at 2:1 (BR-EL-007, BR-EL-008)
        vl_acc = LeaveAccount.objects.filter(employee_id=emp_id, category="VL", year=year).first()
        converted_el = Decimal("0.0")
        if vl_acc and vl_acc.available > 0:
            converted_el = convert_vl_to_el(vl_acc.available)
            LeaveTransaction.objects.create(
                account=vl_acc,
                delta=-vl_acc.available,
                transaction_type="VL_CONVERT_LAPSE",
                reference_id=f"vl_conv_{year}",
            )
            vl_acc.available = Decimal("0.0")
            vl_acc.save(update_fields=["available"])
            summary["converted_vl"] += 1

        # 3. Carry forward EL and COL to next year (BR-EL-005, BR-EL-009)
        el_curr = LeaveAccount.objects.filter(employee_id=emp_id, category="EL", year=year).first()
        carried_el = (el_curr.available if el_curr else Decimal("0.0")) + converted_el

        el_next, _ = LeaveAccount.objects.get_or_create(
            employee_id=emp_id, category="EL", year=next_year
        )
        el_next.allotted += carried_el
        el_next.available += carried_el
        el_next.save(update_fields=["allotted", "available"])
        summary["carried_forward"] += 1

    return summary


def process_sla_sweep(reminder_days: int = 2, escalation_days: int = 5) -> dict:
    """Sweep pending requests and trigger SLA reminders and escalations (BR-EL-032, BR-EL-033)."""
    now = datetime.datetime.now()
    pending_statuses = [
        LeaveStatus.AWAITING_SUBSTITUTE_RESPONSE,
        LeaveStatus.AWAITING_UNIT_HEAD_REVIEW,
        LeaveStatus.AWAITING_ESTABLISHMENT_REVIEW,
        LeaveStatus.AWAITING_SANCTION_AUTHORITY_REVIEW,
    ]
    qs = LeaveRequest.objects.filter(status__in=pending_statuses)
    reminded = 0
    escalated = 0

    for req in qs:
        # Calculate pending age in days
        pending_age = (now - req.created_at.replace(tzinfo=None)).days
        if pending_age >= escalation_days:
            escalated += 1
        elif pending_age >= reminder_days:
            reminded += 1

    return {"pending_checked": qs.count(), "reminded": reminded, "escalated": escalated}
