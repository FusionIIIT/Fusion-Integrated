"""The application state machine (CW-PC-04)."""
from __future__ import annotations

from dataclasses import dataclass, field

DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_REVIEW = "under_review"
SHORTLISTED = "shortlisted"
INTERVIEW_SCHEDULED = "interview_scheduled"
SELECTED = "selected"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"
AUTO_WITHDRAWN = "auto_withdrawn"
OFFER_ISSUED = "offer_issued"
OFFER_ACCEPTED = "offer_accepted"
OFFER_DECLINED = "offer_declined"
OFFER_EXPIRED = "offer_expired"

TERMINAL = frozenset({REJECTED, WITHDRAWN, AUTO_WITHDRAWN, OFFER_ACCEPTED,
                      OFFER_DECLINED, OFFER_EXPIRED})

#: Still in the running, so the auto-withdraw sweep knows what to close.
IN_FLIGHT = frozenset({DRAFT, SUBMITTED, UNDER_REVIEW, SHORTLISTED,
                       INTERVIEW_SCHEDULED, SELECTED, OFFER_ISSUED})

# Explicit per transition rather than inferred, because a recruiter is an outsider.
STUDENT = "student"
STAFF = "staff"           # TPO / placement chairman, via IAM permissions
RECRUITER = "recruiter"   # a company's own account, scoped to its postings
SYSTEM = "system"         # scheduled sweeps: expiry, auto-withdraw


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move an application from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move an application from {frm!r} to {to!r}.")
        self.actor_kind, self.frm, self.to = actor_kind, frm, to


class GuardFailed(Exception):
    def __init__(self, guard: str, message: str = ""):
        super().__init__(message or f"Guard {guard!r} failed.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


def _review(frm: str, to: str, *guards: str) -> Transition:
    """A review decision by the TPO (PC-BR-010) or the owning company (PC-BR-009)."""
    return Transition(frm, to, "placement.application.review",
                      frozenset({STAFF, RECRUITER}), guards)


TRANSITIONS: tuple[Transition, ...] = (
    # -- the student's own moves ------------------------------------------
    Transition(DRAFT, SUBMITTED, "placement.application.create",
               frozenset({STUDENT}),
               ("window_open", "profile_complete", "is_eligible", "may_apply")),

    # -- review and shortlisting (CW-PC-02) ------------------------------
    _review(SUBMITTED, UNDER_REVIEW),
    _review(SUBMITTED, SHORTLISTED),                  # BW-PC-04: Applied to Shortlisted
    _review(SUBMITTED, REJECTED, "has_reason"),
    _review(UNDER_REVIEW, SHORTLISTED),
    _review(UNDER_REVIEW, REJECTED, "has_reason"),
    _review(SHORTLISTED, REJECTED, "has_reason"),

    # -- interviews (BW-PC-05, BW-PC-06) -------------------------------------------
    Transition(SHORTLISTED, INTERVIEW_SCHEDULED,
               "placement.interview.create",
               frozenset({STAFF, RECRUITER}), ("has_scheduled_round",)),
    _review(INTERVIEW_SCHEDULED, SELECTED),
    _review(INTERVIEW_SCHEDULED, REJECTED, "has_reason"),
    _review(INTERVIEW_SCHEDULED, SHORTLISTED),        # round cancelled, back a step

    # -- offers (CW-PC-03) -----------------------------------------------
    Transition(SELECTED, OFFER_ISSUED, "placement.offer.create",
               frozenset({STAFF, RECRUITER}), ("company_authorized",)),
    Transition(SHORTLISTED, OFFER_ISSUED, "placement.offer.create",
               frozenset({STAFF, RECRUITER}), ("company_authorized",)),
    # BW-PC-07: Shortlisted OR Interview Scheduled may receive an offer.
    Transition(INTERVIEW_SCHEDULED, OFFER_ISSUED, "placement.offer.create",
               frozenset({STAFF, RECRUITER}), ("company_authorized",)),

    # The student answers. `offer_window_open` is PC-BR-013.
    Transition(OFFER_ISSUED, OFFER_ACCEPTED, "placement.offer_response.create",
               frozenset({STUDENT}), ("offer_window_open", "policy_allows_accept")),
    Transition(OFFER_ISSUED, OFFER_DECLINED, "placement.offer_response.create",
               frozenset({STUDENT}), ("offer_window_open",)),

    # System only, so nobody can quietly time a student out by hand.
    Transition(OFFER_ISSUED, OFFER_EXPIRED, "placement.offer_expiry.create",
               frozenset({SYSTEM}), ("offer_window_closed",)),

    # Staff only — a company revoking an offer goes through the TPO (PC-BR-029).
    Transition(OFFER_ISSUED, REJECTED, "placement.offer.revoke",
               frozenset({STAFF}), ("has_reason",)),

    # -- withdrawal: a student may pull out of anything not already ended ---
    *(Transition(s, WITHDRAWN, "placement.application.delete",
                 frozenset({STUDENT}))
      for s in (DRAFT, SUBMITTED, UNDER_REVIEW, SHORTLISTED,
                INTERVIEW_SCHEDULED, SELECTED, OFFER_ISSUED)),

    # Placed elsewhere: the sweep closes the rest, per pool_after_offer.
    *(Transition(s, AUTO_WITHDRAWN, "placement.application.revoke",
                 frozenset({SYSTEM}))
      for s in (DRAFT, SUBMITTED, UNDER_REVIEW, SHORTLISTED,
                INTERVIEW_SCHEDULED, SELECTED, OFFER_ISSUED)),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through."""
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted(t.to for t in TRANSITIONS
                  if t.frm == frm
                  and (actor_kind is None or actor_kind in t.actors))
