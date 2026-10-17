"""The leave-request lifecycle as a declarative table.

    CL / RH                 pending -> approved | rejected               (Unit Head, BR-EL-016)
    SCL / EL / COL / VL     pending -> recommended | not_recommended     (Unit Head, BR-EL-017)
                            recommended | not_recommended
                                    -> approved | rejected               (Sanctioning Authority)
    any non-final state     -> withdrawn                                 (applicant, BR-EL-022)

"Not recommended" is not a rejection: the request still goes up (BR-EL-017).
There is no edit transition at all, because a submitted request is never
modified in place (BR-EL-034).
"""
from __future__ import annotations

from dataclasses import dataclass

from .entities import HIGHER_SANCTION, UNIT_HEAD_FINAL, LeaveCategory, LeaveStatus
from .errors import InvalidTransition

P_VIEW = "leave.request.view"          # sees the approvals queue
P_REVIEW = "leave.request.review"      # Unit Head
P_APPROVE = "leave.request.approve"    # Sanctioning Authority
P_WITHDRAW = "leave.request.delete"    # the applicant

S = LeaveStatus


@dataclass(frozen=True)
class Transition:
    frm: LeaveStatus
    to: LeaveStatus
    categories: frozenset[LeaveCategory]
    permissions: frozenset[str]
    by_applicant: bool = False


_AWAITING_SANCTION = (S.RECOMMENDED, S.NOT_RECOMMENDED)

TRANSITIONS: tuple[Transition, ...] = (
    # Unit Head decides CL/RH outright. A sanctioning authority may too.
    *(Transition(S.PENDING, to, UNIT_HEAD_FINAL, frozenset({P_REVIEW, P_APPROVE}))
      for to in (S.APPROVED, S.REJECTED)),
    # Unit Head recommends higher-sanction leave either way...
    *(Transition(S.PENDING, to, HIGHER_SANCTION, frozenset({P_REVIEW}))
      for to in (S.RECOMMENDED, S.NOT_RECOMMENDED)),
    # ...and the Sanctioning Authority makes the final call.
    *(Transition(frm, to, HIGHER_SANCTION, frozenset({P_APPROVE}))
      for frm in _AWAITING_SANCTION for to in (S.APPROVED, S.REJECTED)),
    # Withdrawal is open until final approval, to the applicant alone.
    *(Transition(frm, S.WITHDRAWN, frozenset(LeaveCategory), frozenset({P_WITHDRAW}),
                 by_applicant=True)
      for frm in (S.PENDING, *_AWAITING_SANCTION)),
)


def resolve(frm: str, to: str, category: str, *, permissions: frozenset[str],
            is_applicant: bool) -> Transition:
    """Return the transition, or raise InvalidTransition saying why not."""
    candidates = [t for t in TRANSITIONS
                  if t.frm == frm and t.to == to and category in t.categories]
    if not candidates:
        raise InvalidTransition(frm, to, f"not allowed for {category} leave")
    t = candidates[0]
    if t.by_applicant != is_applicant:
        reason = ("only the applicant can withdraw a request" if t.by_applicant
                  else "you cannot decide your own leave request")
        raise InvalidTransition(frm, to, reason, denied=True)
    if not (t.permissions & permissions):
        raise InvalidTransition(frm, to, "you do not hold the required permission",
                                denied=True)
    return t


def allowed_targets(frm: str, category: str, *, permissions: frozenset[str],
                    is_applicant: bool) -> list[str]:
    """What this actor could do next — the UI shows exactly these buttons."""
    return [str(t.to) for t in TRANSITIONS
            if t.frm == frm and category in t.categories
            and t.by_applicant == is_applicant and t.permissions & permissions]
