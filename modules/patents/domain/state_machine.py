from __future__ import annotations

from dataclasses import dataclass, field

# Lifecycle states for PatentApplication (BW-PMS-01..16, CW-PMS-01..05)
DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_REVIEW = "under_review"
NEEDS_REVISION = "needs_revision"
REJECTED = "rejected"
RESUBMITTED = "resubmitted"
EXPIRED = "expired"
APPEAL_SUBMITTED = "appeal_submitted"
REMANDED = "remanded"
REJECTION_UPHELD = "rejection_upheld"
DECISION_MODIFIED = "decision_modified"
APPROVED = "approved"
ASSIGNMENT_OFFERED = "assignment_offered"
ATTORNEY_ASSIGNED = "attorney_assigned"
PENDING_REVIEW = "pending_review"
ASSESSMENT_IN_PROGRESS = "assessment_in_progress"
FILED = "filed"
GRANTED = "granted"
MAINTENANCE_PENDING = "maintenance_pending"
RENEWED = "renewed"
LAPSED = "lapsed"
WITHDRAWN = "withdrawn"

# Terminal states with no outgoing transitions
TERMINAL = frozenset({WITHDRAWN, EXPIRED, REJECTION_UPHELD, DECISION_MODIFIED, LAPSED})

# In-flight pre-filing statuses potentially eligible for withdrawal
PRE_FILING_STATES = frozenset({
    DRAFT, SUBMITTED, UNDER_REVIEW, NEEDS_REVISION, REJECTED,
    RESUBMITTED, APPROVED, ASSIGNMENT_OFFERED, ATTORNEY_ASSIGNED,
    PENDING_REVIEW, ASSESSMENT_IN_PROGRESS,
})

# Acting roles
APPLICANT = "applicant"
DIRECTOR = "director"
PCC_ADMIN = "pcc_admin"
ATTORNEY = "attorney"
SYSTEM = "system"


class InvalidTransition(Exception):
    def __init__(self, frm: str, to: str):
        super().__init__(f"Cannot move patent application from {frm!r} to {to!r}.")
        self.frm, self.to = frm, to


class ActorNotAllowed(Exception):
    def __init__(self, actor_kind: str, frm: str, to: str):
        super().__init__(
            f"A {actor_kind} may not move patent application from {frm!r} to {to!r}."
        )
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


def _review_transition(frm: str, to: str, *guards: str) -> Transition:
    return Transition(
        frm, to, "patents.application.review",
        frozenset({DIRECTOR}), guards,
    )


TRANSITIONS: tuple[Transition, ...] = (
    # Applicant initial submission (BR-PMS-014..017, BW-PMS-01)
    Transition(
        DRAFT, SUBMITTED, "patents.application.create",
        frozenset({APPLICANT}),
        ("completeness_check", "documents_valid"),
    ),

    # Director assignment by PCC_ADMIN (BR-PMS-022..027, BW-PMS-01)
    Transition(
        SUBMITTED, UNDER_REVIEW, "patents.application.assign_director",
        frozenset({PCC_ADMIN}),
        ("no_coi",),
    ),

    # Director review decisions (BR-PMS-029..031, BW-PMS-01, BW-PMS-02)
    _review_transition(UNDER_REVIEW, APPROVED, "justification_valid"),
    _review_transition(UNDER_REVIEW, NEEDS_REVISION, "justification_valid"),
    _review_transition(UNDER_REVIEW, REJECTED, "justification_valid"),

    # Revision and resubmission within 60 days (BR-PMS-033..036, UC-PMS-005)
    Transition(
        NEEDS_REVISION, RESUBMITTED, "patents.application.update",
        frozenset({APPLICANT}),
        ("within_revision_deadline", "addresses_feedback"),
    ),
    Transition(
        REJECTED, RESUBMITTED, "patents.application.update",
        frozenset({APPLICANT}),
        ("within_revision_deadline", "addresses_feedback"),
    ),

    # 60-day revision expiration sweep (BR-PMS-035, BR-PMS-038)
    Transition(
        NEEDS_REVISION, EXPIRED, "patents.application.expire",
        frozenset({SYSTEM}),
        ("revision_deadline_expired",),
    ),
    Transition(
        REJECTED, EXPIRED, "patents.application.expire",
        frozenset({SYSTEM}),
        ("revision_deadline_expired",),
    ),

    # Re-assignment after resubmission (BR-PMS-035, PMS-AFR-070)
    Transition(
        RESUBMITTED, UNDER_REVIEW, "patents.application.assign_director",
        frozenset({PCC_ADMIN}),
        ("no_coi",),
    ),

    # Appeal against rejection (BR-PMS-092..094, UC-PMS-022)
    Transition(
        REJECTED, APPEAL_SUBMITTED, "patents.application.appeal",
        frozenset({APPLICANT}),
        ("within_appeal_deadline", "has_grounds"),
    ),

    # Director appeal review outcomes (BR-PMS-095, BW-PMS-03..05, UC-PMS-023)
    Transition(
        APPEAL_SUBMITTED, REMANDED, "patents.application.decide_appeal",
        frozenset({DIRECTOR}),
        ("appeal_remanded",),
    ),
    Transition(
        APPEAL_SUBMITTED, REJECTION_UPHELD, "patents.application.decide_appeal",
        frozenset({DIRECTOR}),
        ("appeal_upheld",),
    ),
    Transition(
        APPEAL_SUBMITTED, DECISION_MODIFIED, "patents.application.decide_appeal",
        frozenset({DIRECTOR}),
        ("decision_modified",),
    ),

    # Resubmission after remand (BW-PMS-03)
    Transition(
        REMANDED, RESUBMITTED, "patents.application.update",
        frozenset({APPLICANT}),
        ("addresses_feedback",),
    ),

    # Attorney assignment (BR-PMS-040..045, BR-PMS-127, BW-PMS-06)
    Transition(
        APPROVED, ASSIGNMENT_OFFERED, "patents.attorney.assign",
        frozenset({PCC_ADMIN}),
        ("approved_panel", "no_coi"),
    ),

    # Attorney accept or decline (UC-PMS-011, PMS-AFR-080..081, BW-PMS-06..07)
    Transition(
        ASSIGNMENT_OFFERED, ATTORNEY_ASSIGNED, "patents.attorney.respond_assignment",
        frozenset({ATTORNEY}),
        ("assignment_accepted",),
    ),
    Transition(
        ASSIGNMENT_OFFERED, PENDING_REVIEW, "patents.attorney.respond_assignment",
        frozenset({ATTORNEY}),
        ("assignment_declined",),
    ),

    # Reassignment from PENDING_REVIEW back to ASSIGNMENT_OFFERED (BW-PMS-07)
    Transition(
        PENDING_REVIEW, ASSIGNMENT_OFFERED, "patents.attorney.assign",
        frozenset({PCC_ADMIN}),
        ("approved_panel", "no_coi"),
    ),

    # Assessment in progress (UC-PMS-012, BR-PMS-046)
    Transition(
        ATTORNEY_ASSIGNED, ASSESSMENT_IN_PROGRESS, "patents.assessment.perform",
        frozenset({ATTORNEY}),
    ),

    # External filing recorded (BR-PMS-020, 055..056, 078, 128, 138, 142)
    Transition(
        ASSESSMENT_IN_PROGRESS, FILED, "patents.filing.record",
        frozenset({ATTORNEY}),
        ("agreements_completed", "budget_approved", "filing_format_valid"),
    ),

    # Patent grant recorded (BR-PMS-059)
    Transition(
        FILED, GRANTED, "patents.filing.record",
        frozenset({ATTORNEY, PCC_ADMIN}),
        ("grant_recorded",),
    ),

    # Maintenance tracking and renewal (BR-PMS-059..061, BR-PMS-100, BW-PMS-14..15)
    Transition(
        GRANTED, MAINTENANCE_PENDING, "patents.maintenance.sweep",
        frozenset({SYSTEM}),
        ("maintenance_window_open",),
    ),
    Transition(
        MAINTENANCE_PENDING, RENEWED, "patents.maintenance.decide",
        frozenset({DIRECTOR}),
        ("renewal_approved",),
    ),
    Transition(
        MAINTENANCE_PENDING, LAPSED, "patents.maintenance.decide",
        frozenset({DIRECTOR}),
        ("renewal_declined",),
    ),

    # Pre-filing withdrawal by Applicant (BR-PMS-067..070, BW-PMS-16)
    *(
        Transition(
            s, WITHDRAWN, "patents.application.withdraw",
            frozenset({APPLICANT}),
            ("has_reason", "withdrawal_eligible"),
        )
        for s in (
            DRAFT, SUBMITTED, UNDER_REVIEW, NEEDS_REVISION, APPROVED,
            ATTORNEY_ASSIGNED, PENDING_REVIEW, ASSESSMENT_IN_PROGRESS,
        )
    ),
)

_INDEX = {(t.frm, t.to): t for t in TRANSITIONS}


def resolve(frm: str, to: str, actor_kind: str | None = None) -> Transition:
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
        t.to for t in TRANSITIONS
        if t.frm == frm and (actor_kind is None or actor_kind in t.actors)
    )
