"""Annual lapse, VL-to-EL conversion and carry-forward (BR-EL-002..009, WF-EL-07).

Idempotent: a balance is processed once and then closed, so a second run, or a
worker that died half way, changes nothing that was already done.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.elm.domain import balances as rules
from modules.elm.domain import leave_types as lt
from modules.elm.domain.errors import RuleViolation
from modules.elm.models import LeaveBalance, LeaveTransaction
from modules.elm.services.common import enforcing_rules

BATCH = 200


@dataclass
class YearEndReport:
    year: int
    processed: int = 0
    lapsed_days: Decimal = Decimal(0)
    carried_days: Decimal = Decimal(0)
    converted_el_days: Decimal = Decimal(0)
    #: Users the directory could not place; left open so a later run picks them up.
    skipped_user_ids: list[int] = field(default_factory=list)


def _next_year_row(user_id: int, year: int, leave_type: str, kind: str) -> LeaveBalance:
    row, _ = LeaveBalance.objects.select_for_update().get_or_create(
        user_id=user_id, year=year, leave_type=leave_type,
        defaults={"entitled": lt.credit_for(kind).get(leave_type, Decimal(0))})
    return row


def _credit_next_year(row: LeaveBalance, days: Decimal, kind: LeaveTransaction.Kind,
                      note: str) -> None:
    row.carried_in += days
    row.save(update_fields=["carried_in", "updated_at"])
    LeaveTransaction.objects.create(balance=row, kind=kind, days=days, note=note)


def _close(row: LeaveBalance, kind_of_person: str, report: YearEndReport) -> None:
    plan = rules.plan_year_end(row.leave_type, row.remaining)
    if plan.lapse > 0:
        row.lapsed += plan.lapse
        LeaveTransaction.objects.create(
            balance=row, kind=LeaveTransaction.Kind.LAPSE, days=plan.lapse,
            note=f"Unused {row.leave_type} lapsed")
        report.lapsed_days += plan.lapse
    if plan.carry_forward > 0:
        _credit_next_year(_next_year_row(row.user_id, row.year + 1, row.leave_type,
                                         kind_of_person),
                          plan.carry_forward, LeaveTransaction.Kind.CARRY_IN,
                          f"Carried forward from {row.year}")
        report.carried_days += plan.carry_forward
    if plan.el_credit > 0:
        _credit_next_year(_next_year_row(row.user_id, row.year + 1, lt.EL, kind_of_person),
                          plan.el_credit, LeaveTransaction.Kind.CONVERT_IN,
                          f"Converted from {row.year} VL at 2:1")
        report.converted_el_days += plan.el_credit
    row.closed = True
    row.save(update_fields=["lapsed", "closed", "updated_at"])
    report.processed += 1


def run(year: int, *, force: bool = False) -> YearEndReport:
    """Close `year` for everyone. Refuses a year that is not over unless forced."""
    with enforcing_rules():
        if year >= timezone.localdate().year and not force:
            raise RuleViolation(f"{year} is not over yet.", "WF-EL-07")
    report = YearEndReport(year=year)
    while True:
        ids = list(LeaveBalance.objects.filter(year=year, closed=False)
                   .exclude(user_id__in=report.skipped_user_ids)
                   .values_list("user_id", flat=True).distinct()[:BATCH])
        if not ids:
            return report
        people = directory.get_users(ids)
        for user_id in ids:
            person = people.get(user_id)
            if person is None or person.kind not in (lt.FACULTY, lt.STAFF):
                report.skipped_user_ids.append(user_id)
                continue
            with transaction.atomic():
                rows = LeaveBalance.objects.select_for_update().filter(
                    user_id=user_id, year=year, closed=False)
                # EL first, so VL conversion never lands on a row this pass is closing.
                for row in sorted(rows, key=lambda r: r.leave_type != lt.EL):
                    _close(row, person.kind, report)
