"""MMS declarative state machines.

A table of legal moves per workflow, so an illegal transition is impossible
to express rather than merely rejected, and "who may do this?" has exactly
one answer per edge. Pure Python — the rules test in milliseconds with no DB.

Covers every live basis workflow (BW-MMS-01..16) and composite workflow
(CW-MMS-01..05). Role management (UC-001, BR-MMS-002..007) is not
workflow-grounded and lives in `services/roles.py`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from modules.mms.domain.exceptions import ActorNotAllowed, InvalidTransition

STUDENT = "student"
CARETAKER = "caretaker"
WARDEN = "warden"
MESS_ADMIN = "mess_admin"
SYSTEM = "system"


@dataclass(frozen=True)
class Transition:
    frm: str
    to: str
    permission: str
    actors: frozenset[str]
    guards: tuple[str, ...] = field(default_factory=tuple)


def _caretaker(frm: str, to: str, perm: str, *guards: str) -> Transition:
    return Transition(frm, to, perm, frozenset({CARETAKER}), guards)


def _student(frm: str, to: str, perm: str, *guards: str) -> Transition:
    return Transition(frm, to, perm, frozenset({STUDENT}), guards)


def _system(frm: str, to: str, perm: str, *guards: str) -> Transition:
    return Transition(frm, to, perm, frozenset({SYSTEM}), guards)


# -- Registration (BW-MMS-01, BW-MMS-02, CW-MMS-01; BR-MMS-008/009/010) ---
TRANSITIONS: tuple[Transition, ...] = (
    _caretaker(
        "window_closed", "window_open", "mms.registration.window.manage", "window_info_complete"
    ),
    _student("window_open", "registration_pending", "mms.registration.create", "window_open"),
    _caretaker("registration_pending", "registration_approved", "mms.registration.review"),
    _caretaker("registration_pending", "registration_rejected", "mms.registration.review"),
    # -- Deregistration (BW-MMS-03, BW-MMS-04, CW-MMS-02; BR-MMS-012/013) --
    _student(
        "student_registered",
        "deregistration_pending",
        "mms.deregistration.create",
        "student_registered",
    ),
    _caretaker(
        "deregistration_pending",
        "deregistration_approved_awaiting_date",
        "mms.deregistration.review",
    ),
    _caretaker("deregistration_pending", "deregistration_rejected", "mms.deregistration.review"),
    _system(
        "deregistration_approved_awaiting_date",
        "student_deregistered",
        "mms.deregistration.manage",
        "next_calendar_day",
    ),
    # -- Rebate (BW-MMS-05, BW-MMS-06, BW-MMS-07, CW-MMS-03; BR-MMS-021..025)
    _student(
        "no_rebate",
        "rebate_pending",
        "mms.rebate.create",
        "reason_complete",
        "duration_at_least_3_days",
        "lead_time_at_least_1_day",
        "no_rebate_overlap",
    ),
    _caretaker("rebate_pending", "rebate_approved", "mms.rebate.review"),
    _caretaker(
        "rebate_pending",
        "rebate_approved_modified_dates",
        "mms.rebate.review",
        "dates_modified_permitted",
    ),
    _caretaker("rebate_pending", "rebate_rejected", "mms.rebate.review"),
    # -- Vacation (BW-MMS-08, BW-MMS-09, BW-MMS-10, CW-MMS-04;
    #          BR-MMS-026/027/041) ---------------------------------------
    _student(
        "survey_not_created",
        "survey_open",
        "mms.survey.create",
        "vacation_identified",
        "deadline_set",
        "registered_students_only",
    ),
    _student(
        "survey_open",
        "response_yes",
        "mms.survey_response.create",
        "registered",
        "survey_open",
        "before_deadline",
    ),
    _student(
        "survey_open",
        "response_no",
        "mms.survey_response.create",
        "registered",
        "survey_open",
        "before_deadline",
    ),
    _system(
        "survey_open",
        "response_default_no",
        "mms.survey.manage",
        "deadline_reached",
        "no_explicit_response",
    ),
    # -- Special food (BW-MMS-11..15, CW-MMS-05; BR-MMS-028/029/030/031) --
    _student(
        "no_request", "requested", "mms.special_food.create", "lead_time_at_least_1_calendar_day"
    ),
    _caretaker("requested", "rejected", "mms.special_food.review", "within_decision_period"),
    _system(
        "requested",
        "rejected_default",
        "mms.special_food.manage",
        "decision_period_expired",
        "still_requested",
    ),
    _caretaker("requested", "approved", "mms.special_food.review", "within_decision_period"),
    _caretaker("approved", "served", "mms.special_food.update", "current_state_approved"),
    _caretaker("approved", "cancelled", "mms.special_food.update", "current_state_approved"),
    # -- Billing (BW-MMS-16; BR-MMS-016/017/018/019/030) ------------------
    _system(
        "bill_not_generated",
        "bill_generated",
        "mms.billing.manage",
        "calendar_month_event",
        "billing_inputs_available",
    ),
    _caretaker("bill_generated", "bill_finalized", "mms.billing.approve", "reviewed"),
    _caretaker("bill_finalized", "bill_published", "mms.billing.publish"),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    """The single lookup every write goes through.

    Raises `InvalidTransition` if the move is not in the table, and
    `ActorNotAllowed` if the actor kind is not permitted on that edge.
    """
    t = _INDEX.get((frm, to))
    if t is None:
        raise InvalidTransition(frm, to)
    if actor_kind is not None and actor_kind not in t.actors:
        raise ActorNotAllowed(actor_kind, frm, to)
    return t


def is_legal(frm: str, to: str) -> bool:
    return (frm, to) in _INDEX


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    return sorted(
        t.to for t in TRANSITIONS if t.frm == frm and (actor_kind is None or actor_kind in t.actors)
    )
