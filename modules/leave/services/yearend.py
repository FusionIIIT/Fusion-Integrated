"""Scheduled year-end processing (SF-EL-001, WF-EL-07, BR-EL-002..009)."""
from __future__ import annotations

import logging
from datetime import date

from django.db import transaction

from modules.directory import contracts as directory
from modules.leave.domain.categories import CATEGORIES
from modules.leave.domain.ledger import year_end_entries
from modules.leave.services import accounts, notifications, policy as policy_svc

log = logging.getLogger("fusion.leave.yearend")


@transaction.atomic
def run_year_end(year: int | None = None) -> dict:
    year = year or (date.today().year)
    _, snap = policy_svc.effective_policy()
    employees = directory.get_employees()
    processed = 0
    exceptions: list[str] = []
    for person in employees:
        try:
            accounts.ensure_year_credits(person.user_id, year, snap)
            bals = accounts.balances(person.user_id, year)
            entries = year_end_entries(
                kind=person.kind, year=year, balances=bals, policy=snap)
            for cat, entry_type, amount, memo in entries:
                credit_year = year + 1 if entry_type == "credit" else year
                accounts.post(
                    user_id=person.user_id, category=cat, year=credit_year,
                    amount=amount, entry_type=entry_type, memo=memo,
                )
            processed += 1
        except Exception as exc:  # noqa: BLE001 — report, continue
            exceptions.append(f"{person.user_id}: {exc}")
            log.exception("leave.yearend.failed user=%s", person.user_id)
    notifications.enqueue(
        topic="leave.year_end",
        dedupe_key=f"leave.year_end:{year}",
        subject=f"Year-end leave processing {year}",
        body=f"Processed {processed} employees; {len(exceptions)} exceptions.",
        recipient_email="leave-admin@invalid",
        payload={"exceptions": exceptions, "categories": list(CATEGORIES)},
    )
    return {"processed": processed, "exceptions": exceptions, "year": year}
