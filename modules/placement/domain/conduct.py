"""The debarment ladder (policy rules 18, 19 and 21). Pure functions.

The policy is deliberately discretionary — rule 19 says a student "may be
debarred" and rule 21 vests the decision in the Chairperson. So nothing here
debars anyone. It reads the incidents on record and returns the sanction the
policy *recommends*; applying it stays a human act, recorded as one.

The ladders, quoted:

  19  consent given then failed to appear — "may be debarred from the next two
      campus placement processes. A repeat of such an incident will debar them
      from entire campus placement processes." Waivable: "in any unavoidable
      circumstances, the student may inform the placement cell in writing".
  21  code of conduct — de-registered, re-registration on a fee "acceptable
      only once", after which "debarred from Placement activities in future".
  18  unfair means or a false resume — debarred outright, and rule 18 removes
      the re-registration route that rule 21 would otherwise offer.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class IncidentKind(StrEnum):
    CONSENT_FAILURE = "consent_failure"       # rule 19
    CODE_OF_CONDUCT = "code_of_conduct"       # rule 21
    MISREPRESENTATION = "misrepresentation"   # rule 18


class Sanction(StrEnum):
    NONE = "none"
    BAR_NEXT_TWO = "bar_next_two"     # rule 19, first offence
    DEREGISTER = "deregister"         # rule 21, first offence — fee re-entry
    BAR_SEASON = "bar_season"         # repeat, or rule 18
    BAR_PERMANENT = "bar_permanent"   # rule 21 repeat: no re-registration


#: Rule 19's first tier is scoped to drives, not to the season.
BARRED_DRIVES = 2


@dataclass(frozen=True)
class Recommendation:
    sanction: Sanction
    rule: str
    message: str
    #: False wherever the policy says "may be", so nothing reads as automatic.
    automatic: bool = False


def recommend(kind: IncidentKind, *, prior_incidents: int) -> Recommendation:
    """The sanction the policy points to, given what is already on record.

    `prior_incidents` counts earlier incidents of the SAME kind that were not
    waived — the ladders in 19 and 21 escalate independently of each other.
    """
    if kind is IncidentKind.MISREPRESENTATION:
        return Recommendation(
            Sanction.BAR_SEASON, "18",
            "Rule 18 — a false resume or unfair means debars the student, and "
            "removes the re-registration route in rule 20.")

    if kind is IncidentKind.CONSENT_FAILURE:
        if prior_incidents == 0:
            return Recommendation(
                Sanction.BAR_NEXT_TWO, "19",
                f"Rule 19 — first instance: may be debarred from the next "
                f"{BARRED_DRIVES} campus placement processes.")
        return Recommendation(
            Sanction.BAR_SEASON, "19",
            "Rule 19 — a repeat debars the student from the entire campus "
            "placement process.")

    if prior_incidents == 0:
        return Recommendation(
            Sanction.DEREGISTER, "21",
            "Rule 21 — de-registered. The student may re-register once, on "
            "payment of the re-registration fee, at the Chairperson's "
            "discretion.")
    return Recommendation(
        Sanction.BAR_PERMANENT, "21",
        "Rule 21 — the re-registration route is available only once, so a "
        "second incident debars the student from placement activities.")


def bars_this_drive(*, sanction: Sanction, drives_since_sanction: int) -> bool:
    """Whether a sanction still blocks the drive now being considered.

    Rule 19's first tier expires by being served: two drives pass and the
    student is back in. Season and permanent bars never expire this way.
    """
    if sanction in (Sanction.BAR_SEASON, Sanction.BAR_PERMANENT):
        return True
    if sanction is Sanction.BAR_NEXT_TWO:
        return drives_since_sanction < BARRED_DRIVES
    # DEREGISTER removes the registration itself rather than filtering drives.
    return False
