"""Withdrawal eligibility (BR-PMS-067, 068) and co-inventor consent (BR-PMS-070)."""
from __future__ import annotations

from collections.abc import Iterable

from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import RuleViolation


def check_allowed(status: str, eligible: Iterable[str]) -> None:
    if status in sm.POST_FILING:
        raise RuleViolation("The application has been filed with a patent office, so it can "
                            "no longer be withdrawn in PMS.", code="withdrawal_after_filing")
    if status not in set(eligible):
        raise RuleViolation(
            f"Applications that are {status.replace('_', ' ')} cannot be withdrawn under the "
            f"current PMS settings. Ask the PCC_ADMIN if you believe this is wrong.",
            code="withdrawal_not_eligible")


def check_consent(required: bool, co_inventor_ids: Iterable[int],
                  consented_ids: Iterable[int]) -> None:
    if not required:
        return
    missing = set(co_inventor_ids) - set(consented_ids)
    if missing:
        raise RuleViolation("Every co-inventor must consent to the withdrawal. Confirm the "
                            "consent of each co-inventor listed.", code="consent_missing")
