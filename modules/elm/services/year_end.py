"""Scheduled year-end processing (SF-EL-001, WF-EL-07). Idempotent per year."""
from __future__ import annotations

import logging
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.utils import timezone

from modules.directory import contracts as directory
from modules.elm.domain import categories as c
from modules.elm.domain import policy as policy_domain
from modules.elm.domain.year_end import vl_to_el
from modules.elm.models import LedgerEntry, YearEndRun
from modules.elm.selectors import config as config_sel
from modules.elm.selectors import ledger as ledger_sel
from modules.elm.services import ledger

log = logging.getLogger("fusion.elm.year_end")


def _once(user_id: int, category: str, year: int, entry_type: str, delta: Decimal,
          note: str) -> None:
    try:
        with transaction.atomic():
            LedgerEntry.objects.create(user_id=user_id, category=category, year=year,
                                       entry_type=entry_type, delta=delta, note=note)
    except IntegrityError:
        pass


def run(year: int) -> YearEndRun:
    pv = config_sel.effective_policy()
    run_row, _ = YearEndRun.objects.get_or_create(year=year)
    if run_row.finished_at:
        return run_row
    exceptions: list[dict] = []
    if pv is None:
        run_row.exceptions = [{"error": "No published leave policy; nothing processed."}]
        run_row.save()
        return run_row
    policy = policy_domain.parse(pv.params)
    employees = {e.user_id: e.kind for e in directory.get_employees()}
    for uid in LedgerEntry.objects.values_list("user_id", flat=True).distinct():
        employees.setdefault(uid, "")

    for uid, kind in sorted(employees.items()):
        with transaction.atomic():
            ledger.lock_employee(uid)
            bal = ledger_sel.balances(uid)
            for cat in c.LAPSING:
                if bal[cat] > 0:
                    _once(uid, cat, year, LedgerEntry.LAPSE, -bal[cat], f"{year} lapse")
                elif bal[cat] < 0:
                    exceptions.append({"user_id": uid, "category": cat,
                                       "error": f"negative balance {bal[cat]}"})
            if bal[c.VL] > 0:
                _once(uid, c.VL, year, LedgerEntry.CONVERSION_OUT, -bal[c.VL],
                      f"{year} VL to EL")
                _once(uid, c.EL, year, LedgerEntry.CONVERSION_IN,
                      vl_to_el(bal[c.VL], policy.vl_to_el_ratio), f"{year} from VL")
            for cat in c.CARRY_FORWARD:
                _once(uid, cat, year, LedgerEntry.CARRY_FORWARD, Decimal("0"),
                      f"{year} carried forward {ledger_sel.balances(uid)[cat]}")
            if kind in c.EMPLOYEE_KINDS:
                ledger.ensure_annual_credits(uid, kind, year + 1, policy)
            else:
                exceptions.append({"user_id": uid,
                                   "error": "not in the employee directory; not credited"})
    run_row.employees = len(employees)
    run_row.exceptions = exceptions
    run_row.finished_at = timezone.now()
    run_row.save()
    log.info("elm.year_end year=%s employees=%d exceptions=%d", year,
             len(employees), len(exceptions))
    return run_row
