"""Post-offer obligations (policy rules 22 and 24). Pure functions.

    22  after accepting, a student who will not join must tell the Placement
        Cell "on or before April 15". Silence makes them "liable for any
        further consequences, including referral to the institute for
        disciplinary actions" — a referral this system records but does not
        make.
    24  "No dues certificate ... will not be issued to the placed (on/off
        campus) students unless the signed copy of the offer letter is
        submitted to the Placement Cell."

Rule 24 is the institute's lever, so the answer has to be precise about WHY a
student is blocked: an unexplained hold on a no-dues certificate at the end of a
degree is the kind of thing that ends up in the Dean's office.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RecordState:
    """One placement, as rule 24 sees it."""

    company: str
    has_signed_offer_letter: bool
    #: Rule 22: a student who has declared they will not join still owes the
    #: letter, because the acceptance happened and the record stands.
    declared_not_joining: bool = False


@dataclass(frozen=True)
class Clearance:
    cleared: bool
    #: Empty when cleared. One entry per placement still owing a letter, so the
    #: student is told which company rather than just "blocked".
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
    """Whether rule 24 permits a no-dues certificate.

    A student with no placement is cleared — the rule only bites on the placed.
    """
    blocking = tuple(r.company for r in records if not r.has_signed_offer_letter)
    return Clearance(cleared=not blocking, blocking=blocking)


@dataclass(frozen=True)
class NonJoiningVerdict:
    accepted: bool
    is_late: bool
    message: str


def assess_non_joining(*, declared_on: date, deadline: date | None
                       ) -> NonJoiningVerdict:
    """Rule 22's deadline.

    The declaration is always accepted — refusing it would leave the Placement
    Cell less informed, which is the opposite of what the rule wants. Lateness
    is recorded instead, because that is what rule 22 attaches consequences to.
    """
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
