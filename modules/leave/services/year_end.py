"""Year-end processing (EL-UC-020, EVT-01).

An event trigger, not an actor: nothing here is waiting for a person to click
anything. At the boundary, each account's unused balance meets its outcome
(BR-EL-002..009):

    CL, RH, SCL   lapse
    VL            convert to EL at 2:1, fractions included
    EL, COL       carry forward

Every outcome is a ledger row, because "the year-end run did something to my
VL" is not an acceptable thing to have to explain afterwards. Exceptions are
reported rather than raised, so one odd account cannot stop the boundary for
everybody.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from modules.leave.domain import categories as cat
from modules.leave.models import LeaveBalance, LeavePolicy
from modules.leave.services import accounts

log = logging.getLogger("fusion.leave.year_end")


@dataclass
class YearEndReport:
    year_label: str
    lapsed: list[str] = field(default_factory=list)
    converted: list[str] = field(default_factory=list)
    carried: list[str] = field(default_factory=list)
    exceptions: list[str] = field(default_factory=list)

    def __str__(self) -> str:
        return (f"{self.year_label}: {len(self.lapsed)} lapsed, "
                f"{len(self.converted)} converted, {len(self.carried)} carried, "
                f"{len(self.exceptions)} exception(s)")


def run(*, policy: LeavePolicy, dry_run: bool = False) -> YearEndReport:
    """Close one leave year and open the next."""
    closing = policy.year_label
    opening = accounts.next_year_label(closing)
    report = YearEndReport(closing)

    employee_ids = set(LeaveBalance.objects
                       .filter(year_label=closing)
                       .values_list("user_id", flat=True))

    for user_id in sorted(employee_ids):
        try:
            _close_one(user_id=user_id, closing=closing, opening=opening,
                       policy=policy, report=report, dry_run=dry_run)
        except Exception as exc:
            # One broken account is reported, not raised: the boundary has to
            # happen for everybody else.
            report.exceptions.append(f"{user_id}: {exc}")
            log.exception("leave.year_end.failed user=%s", user_id)

    if not dry_run:
        _open_next(opening=opening, policy=policy, employee_ids=employee_ids)
    return report


def _close_one(*, user_id: int, closing: str, opening: str,
               policy: LeavePolicy, report: YearEndReport,
               dry_run: bool) -> None:
    for row in LeaveBalance.objects.filter(user_id=user_id, year_label=closing):
        available = row.available
        if available < 0:
            report.exceptions.append(
                f"{user_id}/{row.category}: account is over-drawn by "
                f"{-available} and was left alone")
            continue
        if available == 0:
            continue

        action = cat.year_end_action(row.category, available,
                                     vl_per_el=policy.vl_per_el)
        if dry_run:
            _record(report, action, row, user_id)
            continue

        if action.kind == cat.CARRY_FORWARD:
            accounts.carry_forward(user_id=user_id, from_year=closing,
                                   to_year=opening)
        elif action.kind == cat.LAPSE:
            accounts.post(user_id=user_id, year_label=closing,
                          category=row.category, days=-available,
                          kind="year_end_lapse",
                          note=f"Lapsed at the {closing} boundary")
        elif action.kind == cat.CONVERT:
            accounts.post(user_id=user_id, year_label=closing,
                          category=row.category, days=-available,
                          kind="year_end_conversion",
                          note=f"Converted to {action.target} at "
                               f"{policy.vl_per_el}:1")
            accounts.post(user_id=user_id, year_label=opening,
                          category=action.target or cat.EL, days=action.amount,
                          kind="year_end_conversion",
                          note=f"From {closing} VL conversion")
        _record(report, action, row, user_id)


def _record(report: YearEndReport, action, row, user_id: int) -> None:
    label = f"{user_id}/{row.category}={row.available}"
    if action.kind == cat.LAPSE:
        report.lapsed.append(label)
    elif action.kind == cat.CONVERT:
        report.converted.append(f"{label}->{action.amount} {action.target}")
    elif action.kind == cat.CARRY_FORWARD:
        report.carried.append(label)


def _open_next(*, opening: str, policy: LeavePolicy,
               employee_ids: set[int]) -> None:
    """The new year's entitlement, for everyone who had an account."""
    for user_id in sorted(employee_ids):
        person_kind = _kind_for(user_id)
        if person_kind is None:
            continue
        accounts.credit_annual(user_id=user_id, year_label=opening,
                               employee_kind=person_kind, policy=policy)


def _kind_for(user_id: int) -> str | None:
    from modules.directory import contracts as directory

    person = directory.get_users([user_id]).get(user_id)
    return person.kind if person else None
