"""BR-EL-002..009: the year-end run.

Runs once a year, credits the new entitlements, lapses what the policy does not
carry forward, converts Vacation Leave into Earned Leave at the configured
ratio, and carries the balance over. Everything is driven by `domain.year_end`,
so the arithmetic is testable without a database and the run only supplies rows.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.leave.domain import year_end as year_end_domain
from modules.leave.models import (
    CARRY_FORWARD,
    CONVERSION,
    CREDIT,
    LAPSE,
    LeaveBalance,
    LeavePolicy,
)
from modules.leave.services import ledger, notifications

log = logging.getLogger("fusion.leave.yearend")


@dataclass
class YearEndReport:
    year: int
    credited: int = 0
    lapsed: int = 0
    converted: int = 0
    carried: int = 0
    skipped: int = 0
    exceptions: list[dict] = field(default_factory=list)

    def __str__(self) -> str:
        return (f"{self.year}: credited={self.credited} lapsed={self.lapsed} "
                f"converted={self.converted} carried={self.carried} "
                f"skipped={self.skipped} exceptions={len(self.exceptions)}")


def is_due(*, today, policy: LeavePolicy) -> bool:
    """BR-EL-001: the run belongs to the closing year. Run early only when an
    administrator says so, never on a calendar guess alone."""
    return today.month >= policy.year_end_month


def people_in_scope() -> list[int]:
    """Everyone on the payroll. The directory owns that definition."""
    try:
        return sorted(person.user_id for person in directory.get_employees())
    except Exception as exc:  # noqa: BLE001 - directory failure must not stop callers
        log.warning("leave.yearend.directory_unavailable err=%s", exc)
        return []


@transaction.atomic
def run(*, year: int, user_ids: list[int] | None = None, now=None,
        dry_run: bool = False) -> YearEndReport:
    """Close `year` and open `year + 1`. Idempotent per person: a person whose
    balances are already marked processed is skipped rather than credited twice
    (BR-EL-002)."""
    now = now or timezone.now()
    pol = LeavePolicy.objects.first() or LeavePolicy()
    pol_domain = pol.as_domain()
    report = YearEndReport(year=year)

    # Create a mapping of user_id to kind
    employee_kind_map = {user.user_id: user.kind for user in directory.get_employees()}

    for user_id in (user_ids if user_ids is not None else people_in_scope()):
        try:
            employee_kind = employee_kind_map[user_id]
            _run_for_person(
                user_id, year=year, pol_domain=pol_domain, now=now,
                dry_run=dry_run, report=report, employee_kind=employee_kind,
            )
        except Exception as exc:
            # One person's arithmetic never stops the run for the rest (BR-EL-009).
            log.exception("leave.yearend.person_failed user=%s year=%s", user_id, year)
            report.exceptions.append({"user_id": user_id, "error": str(exc)})
            notifications.enqueue(
                topic="leave.year_end.exception",
                dedupe_key=f"year-end-exception:{year}:{user_id}",
                recipient_email=getattr(settings, "OPS_EMAIL", "ops@invalid"),
                subject=f"Leave year-end failed for user {user_id}",
                body=f"Year {year}: {exc}")

    if not dry_run:
        _credit_entitlements(pol, pol_domain, report)
    notifications.enqueue(
        topic="leave.year_end.processed",
        dedupe_key=f"year-end:{year}",
        recipient_email=getattr(settings, "OPS_EMAIL", "ops@invalid"),
        subject=f"Leave year-end {year} processed",
        body=str(report))
    log.info("leave.yearend.done %s", report)
    return report


def _run_for_person(user_id: int, *, year: int, pol_domain, now, dry_run: bool,
                    report: YearEndReport, employee_kind: str) -> None:
    opening = (LeaveBalance.objects
               .filter(user_id=user_id, year=year + 1)
               .exists())
    if opening:
        # Already run for this person: doing it twice would double-credit them.
        report.skipped += 1
        return

    balances = list(LeaveBalance.objects.filter(user_id=user_id, year=year))
    plan = year_end_domain.plan(pol_domain, employee_kind, balances, year)
    postings = []
    for decision in plan:
        if decision.kind == "lapse":
            postings.append(ledger.Posting(
                user_id=user_id, year=year, category=decision.category, kind=LAPSE,
                days=decision.days, note=f"Year-end lapse of {year}"))
            report.lapsed += 1
        elif decision.kind == "carry_forward":
            postings.append(ledger.Posting(
                user_id=user_id, year=year + 1, category=decision.category,
                kind=CARRY_FORWARD, days=decision.days,
                note=f"Carried forward from {year}"))
            report.carried += 1
        elif decision.kind == "conversion":
            postings.append(ledger.Posting(
                user_id=user_id, year=year + 1, category=decision.category,
                kind=CONVERSION, days=decision.days,
                note=f"Vacation converted to Earned Leave for {year + 1}"))
            report.converted += 1

    if dry_run:
        return
    if postings:
        ledger.post(postings, created_by_user_id=None)
    LeaveBalance.objects.filter(user_id=user_id, year=year + 1).update(
        year_end_applied=True)


def _credit_entitlements(pol: LeavePolicy, pol_domain, report: YearEndReport) -> None:
    """BR-EL-004..008: the new year's entitlement, per person kind. Credit is the
    policy's configured figure, not a hard-coded one."""
    next_year = report.year + 1
    for person in directory.get_employees():
        entitlement = _entitlement_for(person.kind, pol)
        if entitlement is None:
            continue
        category = "VL" if person.kind == "faculty" else "EL"
        ledger.post([ledger.Posting(
            user_id=person.user_id, year=next_year, category=category, kind=CREDIT,
            days=Decimal(str(entitlement)),
            note=f"Entitlement for {next_year}")])
        report.credited += 1


def _entitlement_for(kind: str, pol: LeavePolicy) -> float | None:
    return {"faculty": float(pol.vacation_days),
            "staff": float(pol.earned_days)}.get(kind)
