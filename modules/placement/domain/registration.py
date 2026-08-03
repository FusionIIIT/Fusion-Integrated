"""Who may register for a season, and on what terms (rules 1, 20, 21).

Pure functions over plain data.

    1   only registered students participate
    20  register by the stipulated deadline; afterwards a late fee and the
        Placement Cell's approval
    21  a de-registered student may re-register once, on a fee, and never again

Fails closed on a missing academic fact, for the same reason the eligibility
engine does: a student with no declared result cannot be assessed, and absence
must not read as a pass.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Route(StrEnum):
    """How a registration may proceed, if at all."""

    OPEN = "open"                 # within the window, register directly
    LATE = "late"                 # past the deadline: fee + approval (r20)
    REREGISTER = "reregister"     # de-registered: fee, once only (r21)
    REFUSED = "refused"


@dataclass(frozen=True)
class Terms:
    route: Route
    reason: str
    message: str
    #: Rupees the student must have paid. Recorded, never collected here.
    fee: int = 0

    @property
    def allowed(self) -> bool:
        return self.route is not Route.REFUSED


@dataclass(frozen=True)
class Applicant:
    """What the decision reads. `cpi` and `active_backlogs` are None when no
    result has been declared."""

    cpi: Decimal | None = None
    active_backlogs: int | None = None
    current_status: str | None = None      # None = never registered
    reregistration_count: int = 0
    is_permanently_barred: bool = False


@dataclass(frozen=True)
class SeasonTerms:
    is_active: bool = True
    closes_on: date | None = None
    min_cpi: Decimal | None = None
    allow_backlogs: bool = True
    late_fee: int = 0
    reregistration_fee: int = 0


def _refuse(reason: str, message: str) -> Terms:
    return Terms(Route.REFUSED, reason, message)


def assess(season: SeasonTerms, applicant: Applicant, *, today: date) -> Terms:
    """The route open to this student right now."""
    if not season.is_active:
        return _refuse("season_closed",
                       "Registration for this season is closed.")

    if applicant.is_permanently_barred:
        # Rule 21(ii): the re-registration route is available once only.
        return _refuse("barred",
                       "You are debarred from placement activities and cannot "
                       "register.")

    if applicant.current_status == "registered":
        return _refuse("already_registered", "You are already registered.")

    if applicant.current_status == "debarred":
        return _refuse("debarred",
                       "A debarment is in force. Contact the Placement Cell.")

    # Academic eligibility, before anything about fees or dates.
    if season.min_cpi is not None:
        if applicant.cpi is None:
            return _refuse(
                "no_declared_result",
                "Your latest result has not been declared yet, so your CPI "
                "cannot be checked. Registration opens once it is.")
        if applicant.cpi < season.min_cpi:
            return _refuse(
                "cpi_below_minimum",
                f"Registration needs a CPI of at least {season.min_cpi}; "
                f"yours is {applicant.cpi}.")

    if not season.allow_backlogs:
        if applicant.active_backlogs is None:
            return _refuse(
                "no_declared_result",
                "Your latest result has not been declared yet, so your "
                "backlogs cannot be checked.")
        if applicant.active_backlogs > 0:
            return _refuse(
                "has_backlogs",
                f"Registration is closed to students with active backlogs; "
                f"you have {applicant.active_backlogs}.")

    # Rule 21: coming back after de-registration is its own route.
    if applicant.current_status == "opted_out":
        if applicant.reregistration_count >= 1:
            return _refuse(
                "reregistration_spent",
                "Re-registration is allowed once only, and has already been "
                "used.")
        return Terms(
            Route.REREGISTER, "reregistration",
            f"Re-registration needs the ₹{season.reregistration_fee} fee and "
            f"the Chairperson's approval (rule 21).",
            fee=season.reregistration_fee)

    # Rule 20: on time, or late with a fee.
    if season.closes_on is not None and today > season.closes_on:
        return Terms(
            Route.LATE, "late",
            f"Registration closed on {season.closes_on}. You may still "
            f"register on payment of the ₹{season.late_fee} late fee, subject "
            f"to the Placement Cell's approval (rule 20).",
            fee=season.late_fee)

    return Terms(Route.OPEN, "open", "You can register now.")
