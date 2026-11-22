"""The scholarship application state machine (CW-SPACS-01, CW-SPACS-02).

A declarative table of legal transitions and guards.
Pure Python — no Django, DRF or Celery. Testable in milliseconds with no database.
"""
from __future__ import annotations

from dataclasses import dataclass, field

# State constants
DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_VERIFICATION = "under_verification"
CORRECTION_REQUIRED = "correction_required"
RESUBMITTED = "resubmitted"
VERIFIED = "verified"
VERIFICATION_CONCERN = "verification_concern"
UNDER_CONVENER_REVIEW = "under_convener_review"
APPROVED = "approved"
REJECTED = "rejected"
WITHDRAWN = "withdrawn"

ALL_STATES = frozenset({
    DRAFT,
    SUBMITTED,
    UNDER_VERIFICATION,
    CORRECTION_REQUIRED,
    RESUBMITTED,
    VERIFIED,
    VERIFICATION_CONCERN,
    UNDER_CONVENER_REVIEW,
    APPROVED,
    REJECTED,
    WITHDRAWN,
})

TERMINAL = frozenset({APPROVED, REJECTED, WITHDRAWN})

#: States from which a student is permitted to withdraw before final decision (BR-SPACS-009)
WITHDRAWABLE = frozenset({
    SUBMITTED,
    UNDER_VERIFICATION,
    CORRECTION_REQUIRED,
    VERIFIED,
})

#: States in which student is permitted to modify application data (BR-SPACS-010)
EDITABLE = frozenset({
    DRAFT,
    SUBMITTED,
    CORRECTION_REQUIRED,
})

# Actor roles
STUDENT = "student"
ASSISTANT = "spacs_assistant"
CONVENER = "spacs_convener"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move application from {frm!r} to {to!r}.")
        self.frm = frm
        self.to = to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(f"A {actor_kind} may not move an application from {frm!r} to {to!r}.")
        self.actor_kind = actor_kind
        self.frm = frm
        self.to = to


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


TRANSITIONS: tuple[Transition, ...] = (
    # --- Student submission ---
    Transition(
        DRAFT,
        SUBMITTED,
        "spacs.application.create",
        frozenset({STUDENT}),
        ("window_open", "eligibility_passed", "completeness_passed", "no_duplicate"),
    ),
    # --- Assistant verification workflow (BW-SPACS-01, BW-SPACS-02, BW-SPACS-06) ---
    Transition(
        SUBMITTED,
        UNDER_VERIFICATION,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        (),
    ),
    Transition(
        UNDER_VERIFICATION,
        CORRECTION_REQUIRED,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        ("has_reason",),
    ),
    Transition(
        CORRECTION_REQUIRED,
        RESUBMITTED,
        "spacs.application.update",
        frozenset({STUDENT}),
        ("completeness_passed",),
    ),
    Transition(
        RESUBMITTED,
        UNDER_VERIFICATION,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        (),
    ),
    Transition(
        RESUBMITTED,
        VERIFIED,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        (),
    ),
    Transition(
        UNDER_VERIFICATION,
        VERIFIED,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        (),
    ),
    Transition(
        UNDER_VERIFICATION,
        VERIFICATION_CONCERN,
        "spacs.application.review",
        frozenset({ASSISTANT}),
        ("has_reason",),
    ),
    # --- Convener decision workflow (BW-SPACS-03, BW-SPACS-04, BW-SPACS-07, BW-SPACS-10) ---
    Transition(
        VERIFIED,
        UNDER_CONVENER_REVIEW,
        "spacs.application.approve",
        frozenset({CONVENER}),
        (),
    ),
    Transition(
        VERIFICATION_CONCERN,
        UNDER_CONVENER_REVIEW,
        "spacs.application.approve",
        frozenset({CONVENER}),
        (),
    ),
    Transition(
        UNDER_CONVENER_REVIEW,
        APPROVED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        (),
    ),
    Transition(
        UNDER_CONVENER_REVIEW,
        REJECTED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        ("has_reason",),
    ),
    Transition(
        UNDER_CONVENER_REVIEW,
        CORRECTION_REQUIRED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        ("has_reason",),
    ),
    # Direct decision edges
    Transition(
        VERIFIED,
        APPROVED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        (),
    ),
    Transition(
        VERIFIED,
        REJECTED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        ("has_reason",),
    ),
    Transition(
        VERIFICATION_CONCERN,
        APPROVED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        (),
    ),
    Transition(
        VERIFICATION_CONCERN,
        REJECTED,
        "spacs.application.approve",
        frozenset({CONVENER}),
        ("has_reason",),
    ),
    # --- Student cross-cutting withdrawal (BW-SPACS-05, BR-SPACS-009) ---
    Transition(
        SUBMITTED,
        WITHDRAWN,
        "spacs.application.delete",
        frozenset({STUDENT}),
        (),
    ),
    Transition(
        UNDER_VERIFICATION,
        WITHDRAWN,
        "spacs.application.delete",
        frozenset({STUDENT}),
        (),
    ),
    Transition(
        CORRECTION_REQUIRED,
        WITHDRAWN,
        "spacs.application.delete",
        frozenset({STUDENT}),
        (),
    ),
    Transition(
        VERIFIED,
        WITHDRAWN,
        "spacs.application.delete",
        frozenset({STUDENT}),
        ("not_under_review",),
    ),
)


def is_legal(frm: str, to: str, actor_kind: str | None = None) -> bool:
    for t in TRANSITIONS:
        if t.frm == frm and t.to == to:
            if actor_kind is None or actor_kind in t.actors:
                return True
    return False


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
    matching = [t for t in TRANSITIONS if t.frm == frm and t.to == to]
    if not matching:
        raise InvalidTransition(frm, to)
    if actor_kind is not None:
        allowed = [t for t in matching if actor_kind in t.actors]
        if not allowed:
            raise ActorNotAllowed(actor_kind, frm, to)
        return allowed[0]
    return matching[0]


def allowed_targets(frm: str, actor_kind: str | None = None) -> list[str]:
    targets = []
    for t in TRANSITIONS:
        if t.frm == frm:
            if actor_kind is None or actor_kind in t.actors:
                if t.to not in targets:
                    targets.append(t.to)
    return targets
