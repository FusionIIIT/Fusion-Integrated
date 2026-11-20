"""Post-offer obligations (policy rules 22 and 24)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RecordState:
    """One placement, as rule 24 sees it."""

    company: str
    has_signed_offer_letter: bool
    #: Rule 22: declaring "not joining" does not release the letter obligation.
    declared_not_joining: bool = False


@dataclass(frozen=True)
class Clearance:
    cleared: bool
    #: One entry per placement still owing a letter, so the student is told which.
    blocking: tuple[str, ...] = ()

    @property
    def message(self) -> str:
        if self.cleared:
            return "No placement obligation is outstanding."
        companies = ", ".join(self.blocking)
        return (f"A signed offer letter has not been submitted for: "
                f"{companies}. Rule 24 withholds the no-dues certificate "
                f"until it is.")


def no_dues_clearance(records: tuple[RecordState, ...]) -> Clearance:
    """Whether rule 24 permits a no-dues certificate."""
    blocking = tuple(r.company for r in records if not r.has_signed_offer_letter)
    return Clearance(cleared=not blocking, blocking=blocking)


@dataclass(frozen=True)
class NonJoiningVerdict:
    accepted: bool
    is_late: bool
    message: str


def assess_non_joining(*, declared_on: date, deadline: date | None
                       ) -> NonJoiningVerdict:
    """Rule 22's deadline."""
    if deadline is None:
        return NonJoiningVerdict(
            True, False,
            "Recorded. No cut-off is configured for this season.")
    if declared_on <= deadline:
        return NonJoiningVerdict(
            True, False,
            f"Recorded within the rule 22 cut-off of {deadline}.")
    return NonJoiningVerdict(
        True, True,
        f"Recorded, but after the rule 22 cut-off of {deadline}. The Placement "
        f"Cell may refer this to the institute.")
