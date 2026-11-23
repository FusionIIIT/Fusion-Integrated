"""External filing: the prerequisites (BR-PMS-128) and what a recorded filing must carry."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date

from modules.pms.domain.errors import InvalidInput
from modules.pms.domain.policy import JURISDICTION

NO_RULES = "not_validated_no_rules"      # BR-PMS-055: no patent-office format rules exist
EXTERNAL_ID = re.compile(r"^[A-Za-z0-9/._ -]{3,64}$")


@dataclass(frozen=True)
class InventorState:
    name: str
    agreement_completed: bool
    consent_recorded: bool


@dataclass(frozen=True)
class FilingFacts:
    has_accepted_attorney: bool
    has_approved_budget: bool
    inventors: tuple[InventorState, ...]


def filing_blockers(facts: FilingFacts) -> list[str]:
    """Every unmet prerequisite, each as a sentence; an empty list means filing may proceed."""
    blockers = []
    if not facts.has_accepted_attorney:
        blockers.append("An attorney must have accepted the assignment.")
    if not facts.has_approved_budget:                                       # BR-PMS-128
        blockers.append("The filing budget must be approved, by the Director or by the "
                        "outside authority after an escalation.")
    if not facts.inventors:
        blockers.append("The application lists no inventors.")
    for inv in facts.inventors:
        if not inv.agreement_completed:                                     # BR-PMS-020, 078
            blockers.append(f"{inv.name}'s inventor agreement is not recorded as complete.")
        if not inv.consent_recorded:                                        # BR-PMS-075
            blockers.append(f"{inv.name}'s consent to filing is not recorded.")
    return blockers


def check_filing(*, jurisdiction: str, external_filing_id: str, filing_date: date,
                 confirmation_reference: str, today: date) -> None:
    """BR-PMS-142 / PMS-AFR-104: a filing is recorded only with its external evidence."""
    if not JURISDICTION.match(jurisdiction or ""):
        raise InvalidInput("Give the patent office's jurisdiction code, such as IN, EP or US.",
                           code="invalid_jurisdiction")
    if not EXTERNAL_ID.match((external_filing_id or "").strip()):
        raise InvalidInput("Enter the application number the patent office issued "
                           "(3-64 letters, digits, '/', '.', '-' or spaces).",
                           code="invalid_filing_id")
    if not (confirmation_reference or "").strip():
        raise InvalidInput("Enter the patent office's filing confirmation; PMS records a "
                           "filing only once the office has confirmed it.",
                           code="confirmation_required")
    if filing_date > today:
        raise InvalidInput("The filing date cannot be in the future.",
                           code="filing_date_in_future")
