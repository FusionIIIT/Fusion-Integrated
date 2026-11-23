"""Appeal timing (BR-PMS-093) and what each outcome does next (ruling C8)."""
from __future__ import annotations

from datetime import date

from modules.pms.domain.errors import InvalidInput, RuleViolation

UPHOLD, REMAND, MODIFY = "uphold", "remand", "modify"
OUTCOMES = (UPHOLD, REMAND, MODIFY)                       # BR-PMS-095
MODIFIED_DECISIONS = ("approve", "needs_revision")        # ruling C8


def check_open(today: date, appeal_due_on: date | None, revision_due_on: date | None) -> None:
    if appeal_due_on is None or today > appeal_due_on:
        raise RuleViolation("The period for appealing this rejection has ended.",
                            code="appeal_period_over")
    if revision_due_on is not None and today > revision_due_on:
        raise RuleViolation("The 60-day period after the rejection has ended, so the "
                            "application has expired.", code="revision_period_over")


def application_event(outcome: str, modified_decision: str | None) -> str:
    """The APPLICATION table event an appeal outcome drives."""
    if outcome == UPHOLD:
        return "appeal_upheld"
    if outcome == REMAND:
        return "appeal_remanded"
    if outcome == MODIFY and modified_decision == "approve":
        return "appeal_modified_approve"
    if outcome == MODIFY and modified_decision == "needs_revision":
        return "appeal_modified_revise"
    if outcome == MODIFY:
        raise InvalidInput("When modifying the decision, choose Approve or Needs Revision.",
                           code="modified_decision_required")
    raise InvalidInput("Choose Uphold Rejection, Remand for Amendment or Modify Decision.",
                       code="invalid_outcome")
