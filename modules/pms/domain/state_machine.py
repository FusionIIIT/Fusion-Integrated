"""Declarative transition tables (PMS-AFR-225): a move absent from a table cannot happen."""
from __future__ import annotations

from dataclasses import dataclass

from modules.pms.domain.errors import ActorNotAllowed, InvalidTransition

APPLICANT = "applicant"
DIRECTOR = "director"
PCC_ADMIN = "pcc_admin"
ATTORNEY = "attorney"
SYSTEM = "system"
ACTORS = (APPLICANT, DIRECTOR, PCC_ADMIN, ATTORNEY, SYSTEM)

# Pseudo-state for the event that creates a record.
NEW = "new"

DRAFT = "draft"
SUBMITTED = "submitted"
UNDER_REVIEW = "under_review"
NEEDS_REVISION = "needs_revision"
REJECTED = "rejected"
RESUBMITTED = "resubmitted"
APPROVED = "approved"
ATTORNEY_ASSIGNED = "attorney_assigned"
PENDING_REVIEW = "pending_review"
APPEAL_SUBMITTED = "appeal_submitted"
REJECTION_UPHELD = "rejection_upheld"
EXPIRED = "expired"
WITHDRAWN = "withdrawn"
FILED = "filed"
GRANTED = "granted"
REFUSED = "refused"

APPLICATION_STATUSES = (
    DRAFT, SUBMITTED, UNDER_REVIEW, NEEDS_REVISION, REJECTED, RESUBMITTED, APPROVED,
    ATTORNEY_ASSIGNED, PENDING_REVIEW, APPEAL_SUBMITTED, REJECTION_UPHELD, EXPIRED,
    WITHDRAWN, FILED, GRANTED, REFUSED,
)
TERMINAL = frozenset({WITHDRAWN, EXPIRED, REJECTION_UPHELD, REFUSED})
POST_FILING = frozenset({FILED, GRANTED, REFUSED})
# CW-PMS-05: the only statuses a withdrawal may start from.
WITHDRAWAL_CANDIDATES = (SUBMITTED, UNDER_REVIEW, NEEDS_REVISION, REJECTED, APPROVED,
                         ATTORNEY_ASSIGNED, PENDING_REVIEW)
# BR-PMS-052 as ruled (B5): Director-approved and not yet filed.
BUDGET_STATUSES = frozenset({APPROVED, PENDING_REVIEW, ATTORNEY_ASSIGNED})
# BR-PMS-040 / BR-PMS-127 as ruled (B5).
ATTORNEY_ASSIGNABLE = frozenset({APPROVED, PENDING_REVIEW})
REVISABLE = frozenset({NEEDS_REVISION, REJECTED})
APPLICANT_EDITABLE = frozenset({DRAFT, NEEDS_REVISION, REJECTED})
AWAITING_DIRECTOR = frozenset({SUBMITTED, RESUBMITTED})


@dataclass(frozen=True)
class Transition:
    frm: str
    event: str
    to: str
    actors: frozenset[str]


class Machine:
    def __init__(self, name: str, transitions: tuple[Transition, ...],
                 terminal: frozenset[str] = frozenset()):
        self.name = name
        self.transitions = transitions
        self.terminal = terminal
        self._index: dict[tuple[str, str], Transition] = {}
        for t in transitions:
            if (t.frm, t.event) in self._index:
                raise ValueError(f"{name}: duplicate edge {t.frm}/{t.event}")
            if t.frm in terminal:
                raise ValueError(f"{name}: edge leaves terminal state {t.frm}")
            self._index[(t.frm, t.event)] = t

    @property
    def states(self) -> frozenset[str]:
        return frozenset({t.frm for t in self.transitions} | {t.to for t in self.transitions}
                         | self.terminal) - {NEW}

    @property
    def events(self) -> frozenset[str]:
        return frozenset(t.event for t in self.transitions)

    def resolve(self, frm: str, event: str, actor: str) -> Transition:
        t = self._index.get((frm, event))
        if t is None:
            raise InvalidTransition(self.name, frm, event)
        if actor not in t.actors:
            raise ActorNotAllowed(self.name, frm, event, actor)
        return t

    def is_legal(self, frm: str, event: str) -> bool:
        return (frm, event) in self._index

    def events_for(self, frm: str, actor: str) -> list[str]:
        return sorted(t.event for t in self.transitions if t.frm == frm and actor in t.actors)


def _t(frm: str, event: str, to: str, *actors: str) -> Transition:
    return Transition(frm, event, to, frozenset(actors))


APPLICATION = Machine("application", (
    _t(DRAFT, "submit", SUBMITTED, APPLICANT),                              # BW-PMS-01
    _t(SUBMITTED, "assign_director", UNDER_REVIEW, PCC_ADMIN, SYSTEM),      # BW-PMS-01
    _t(RESUBMITTED, "assign_director", UNDER_REVIEW, PCC_ADMIN, SYSTEM),    # BW-PMS-02
    _t(UNDER_REVIEW, "reassign_director", UNDER_REVIEW, PCC_ADMIN),         # ruling C10
    _t(UNDER_REVIEW, "approve", APPROVED, DIRECTOR),                        # BW-PMS-01
    _t(UNDER_REVIEW, "request_revision", NEEDS_REVISION, DIRECTOR),         # BW-PMS-02
    _t(UNDER_REVIEW, "reject", REJECTED, DIRECTOR),                         # BW-PMS-03..05
    _t(NEEDS_REVISION, "resubmit", RESUBMITTED, APPLICANT),                 # BR-PMS-033
    _t(REJECTED, "resubmit", RESUBMITTED, APPLICANT),                       # BR-PMS-034
    _t(REJECTED, "appeal", APPEAL_SUBMITTED, APPLICANT),                    # BR-PMS-092
    _t(APPEAL_SUBMITTED, "appeal_remanded", NEEDS_REVISION, SYSTEM),        # BW-PMS-03, C8
    _t(APPEAL_SUBMITTED, "appeal_modified_approve", APPROVED, SYSTEM),      # BW-PMS-05, C8
    _t(APPEAL_SUBMITTED, "appeal_modified_revise", NEEDS_REVISION, SYSTEM),  # BW-PMS-05, C8
    _t(APPEAL_SUBMITTED, "appeal_upheld", REJECTION_UPHELD, SYSTEM),        # BW-PMS-04
    _t(APPROVED, "attorney_accepted", ATTORNEY_ASSIGNED, SYSTEM),           # BW-PMS-06
    _t(PENDING_REVIEW, "attorney_accepted", ATTORNEY_ASSIGNED, SYSTEM),     # BW-PMS-07
    _t(APPROVED, "attorney_declined", PENDING_REVIEW, SYSTEM),              # BW-PMS-07
    _t(PENDING_REVIEW, "attorney_declined", PENDING_REVIEW, SYSTEM),        # BW-PMS-07
    _t(ATTORNEY_ASSIGNED, "file", FILED, ATTORNEY),                         # BW-PMS-11
    _t(FILED, "grant", GRANTED, ATTORNEY),                                  # ruling C9
    _t(FILED, "refuse", REFUSED, ATTORNEY),                                 # ruling C9
    _t(NEEDS_REVISION, "expire", EXPIRED, SYSTEM),                          # BR-PMS-038
    _t(REJECTED, "expire", EXPIRED, SYSTEM),                                # BR-PMS-038
    *(_t(s, "withdraw", WITHDRAWN, APPLICANT) for s in WITHDRAWAL_CANDIDATES),  # CW-PMS-05
), terminal=TERMINAL)

OFFERED = "offered"
ACCEPTED = "accepted"
DECLINED = "declined"
CANCELLED = "cancelled"

ASSIGNMENT = Machine("attorney_assignment", (
    _t(NEW, "offer", OFFERED, PCC_ADMIN),                                   # BW-PMS-06
    _t(OFFERED, "accept", ACCEPTED, ATTORNEY),                              # BW-PMS-06
    _t(OFFERED, "decline", DECLINED, ATTORNEY),                             # BW-PMS-07
    _t(OFFERED, "cancel", CANCELLED, SYSTEM),
), terminal=frozenset({DECLINED, CANCELLED}))
LIVE_ASSIGNMENT = frozenset({OFFERED, ACCEPTED})

PROPOSED = "proposed"
BUDGET_APPROVED = "approved"
BUDGET_REJECTED = "rejected"
ESCALATED = "escalated"
ESCALATION_TRACKED = "escalation_tracked"
EXTERNAL_APPROVED = "external_approved"
EXTERNAL_REJECTED = "external_rejected"
BUDGET_CLOSED = "closed"

BUDGET = Machine("budget", (
    _t(NEW, "propose", PROPOSED, ATTORNEY),                                 # ruling C14
    _t(PROPOSED, "approve", BUDGET_APPROVED, DIRECTOR),                     # BW-PMS-08
    _t(PROPOSED, "reject", BUDGET_REJECTED, DIRECTOR),                      # BW-PMS-09
    _t(PROPOSED, "escalate", ESCALATED, DIRECTOR),                          # BW-PMS-10
    _t(ESCALATED, "route", ESCALATION_TRACKED, PCC_ADMIN),                  # BW-PMS-10
    _t(ESCALATION_TRACKED, "record_external_approval", EXTERNAL_APPROVED, PCC_ADMIN),
    _t(ESCALATION_TRACKED, "record_external_rejection", EXTERNAL_REJECTED, PCC_ADMIN),
    _t(PROPOSED, "close", BUDGET_CLOSED, SYSTEM),
    _t(ESCALATED, "close", BUDGET_CLOSED, SYSTEM),
    _t(ESCALATION_TRACKED, "close", BUDGET_CLOSED, SYSTEM),
), terminal=frozenset({BUDGET_APPROVED, BUDGET_REJECTED, EXTERNAL_APPROVED,
                       EXTERNAL_REJECTED, BUDGET_CLOSED}))
OPEN_BUDGET = frozenset({PROPOSED, ESCALATED, ESCALATION_TRACKED})
APPROVED_BUDGET = frozenset({BUDGET_APPROVED, EXTERNAL_APPROVED})

RECORDED = "recorded"
AWAITING_APPLICANT = "awaiting_applicant_approval"
APPLICANT_APPROVED = "applicant_approved"
RESPONSE_READY = "response_ready"
RESPONSE_SUBMITTED = "submitted"

OFFICE_ACTION = Machine("office_action", (
    _t(RECORDED, "prepare_for_applicant", AWAITING_APPLICANT, ATTORNEY),    # BW-PMS-12
    _t(RECORDED, "prepare_ready", RESPONSE_READY, ATTORNEY),                # BW-PMS-13
    _t(AWAITING_APPLICANT, "applicant_approve", APPLICANT_APPROVED, APPLICANT),  # BW-PMS-12
    _t(APPLICANT_APPROVED, "submit", RESPONSE_SUBMITTED, ATTORNEY),         # BW-PMS-12
    _t(RESPONSE_READY, "submit", RESPONSE_SUBMITTED, ATTORNEY),             # BW-PMS-13
), terminal=frozenset({RESPONSE_SUBMITTED}))

SCHEDULED = "scheduled"
DECISION_REQUESTED = "decision_requested"
RENEW_APPROVED = "renew_approved"
DO_NOT_RENEW = "do_not_renew"
RENEWED = "renewed"

MAINTENANCE = Machine("maintenance_cycle", (
    _t(SCHEDULED, "request", DECISION_REQUESTED, ATTORNEY),                 # BW-PMS-14
    _t(DECISION_REQUESTED, "renew", RENEW_APPROVED, DIRECTOR),              # BW-PMS-14
    _t(DECISION_REQUESTED, "do_not_renew", DO_NOT_RENEW, DIRECTOR),         # BW-PMS-15
    _t(DECISION_REQUESTED, "reassign_decider", DECISION_REQUESTED, PCC_ADMIN),  # ruling C19
    _t(RENEW_APPROVED, "record_action", RENEWED, ATTORNEY),                 # BW-PMS-14
), terminal=frozenset({DO_NOT_RENEW, RENEWED}))
LIVE_CYCLE = frozenset({SCHEDULED, DECISION_REQUESTED, RENEW_APPROVED})

APPEAL_OPEN = "open"
APPEAL_DECIDED = "decided"

APPEAL = Machine("appeal", (
    _t(APPEAL_OPEN, "uphold", APPEAL_DECIDED, DIRECTOR),                    # BW-PMS-04
    _t(APPEAL_OPEN, "remand", APPEAL_DECIDED, DIRECTOR),                    # BW-PMS-03
    _t(APPEAL_OPEN, "modify", APPEAL_DECIDED, DIRECTOR),                    # BW-PMS-05
), terminal=frozenset({APPEAL_DECIDED}))

LICENSING_SUBMITTED = "submitted"
LICENSING_ROUTED = "routed"
NEGOTIATING = "negotiating"
AGREEMENT_RECORDED = "agreement_recorded"

LICENSING = Machine("licensing_request", (
    _t(LICENSING_SUBMITTED, "route", LICENSING_ROUTED, SYSTEM, PCC_ADMIN),  # BR-PMS-088
    _t(LICENSING_ROUTED, "add_note", NEGOTIATING, DIRECTOR, PCC_ADMIN),     # PMS-AFR-161
    _t(NEGOTIATING, "add_note", NEGOTIATING, DIRECTOR, PCC_ADMIN),          # PMS-AFR-161
    _t(NEGOTIATING, "record_agreement", AGREEMENT_RECORDED, DIRECTOR, PCC_ADMIN),  # PMS-AFR-162
), terminal=frozenset({AGREEMENT_RECORDED}))

MACHINES = (APPLICATION, ASSIGNMENT, BUDGET, OFFICE_ACTION, MAINTENANCE, APPEAL, LICENSING)
