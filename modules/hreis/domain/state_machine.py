"""Declarative state transitions for HR-EIS requests."""

from __future__ import annotations

from dataclasses import dataclass

EMPLOYEE = "employee"
HR_ADMINISTRATOR = "hr_administrator"
APPROVING_AUTHORITY = "approving_authority"
ACCOUNTANT = "accountant"

DRAFT = "draft"
SUBMITTED = "submitted"
PENDING_CURRENT_AUTHORITY = "pending_current_authority"
PENDING_NEXT_AUTHORITY = "pending_next_authority"
AWAITING_HR_VERIFICATION = "awaiting_hr_verification"
REVIEWER_ASSIGNED_PENDING_REVIEW = "reviewer_assigned_pending_review"
APPROVED_LEAVE_BALANCE_UPDATED = "approved_leave_balance_updated"
APPROVED_LTC_CLAIM = "approved_ltc_claim"
APPROVED_CPDA_CLAIM = "approved_cpda_claim"
REJECTED = "rejected"
FINALIZED_ARCHIVED_CLOSED = "finalized_archived_closed"
PROCESSED_FINANCIAL_STATUS_RECORDED = "processed_financial_status_recorded"


class InvalidTransition(Exception):
    def __init__(self, resource: str, state: str, event: str):
        super().__init__(f"Cannot {event!r} a {resource} request in state {state!r}.")
        self.resource, self.state, self.event = resource, state, event


class ActorNotAllowed(Exception):
    def __init__(self, actor: str, resource: str, event: str):
        super().__init__(f"Actor {actor!r} may not {event!r} a {resource} request.")
        self.actor, self.resource, self.event = actor, resource, event


class GuardFailed(Exception):
    def __init__(self, guard: str):
        super().__init__(f"Required condition {guard!r} is not satisfied.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    resource: str
    source: str
    event: str
    actor: str
    target: str
    guards: tuple[str, ...] = ()


TRANSITIONS = (
    Transition(
        "leave",
        DRAFT,
        "submit",
        EMPLOYEE,
        PENDING_CURRENT_AUTHORITY,
        (
            "valid_required_fields",
            "supported_leave_type",
            "balance_and_eligibility",
            "route_exists",
        ),
    ),
    *(
        Transition(
            "leave",
            state,
            "approve",
            APPROVING_AUTHORITY,
            APPROVED_LEAVE_BALANCE_UPDATED,
            ("current_actor_is_authority", "is_not_request_owner", "final_authority"),
        )
        for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
    ),
    *(
        Transition(
            "leave",
            state,
            "reject",
            APPROVING_AUTHORITY,
            REJECTED,
            ("current_actor_is_authority", "is_not_request_owner"),
        )
        for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
    ),
    *(
        Transition(
            "leave",
            state,
            "forward",
            APPROVING_AUTHORITY,
            PENDING_NEXT_AUTHORITY,
            (
                "current_actor_is_authority",
                "is_not_request_owner",
                "configured_next_authority_exists",
            ),
        )
        for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
    ),
    Transition("appraisal", DRAFT, "submit", EMPLOYEE, SUBMITTED, ("window_open",)),
    Transition(
        "appraisal",
        SUBMITTED,
        "assign_reviewers",
        HR_ADMINISTRATOR,
        REVIEWER_ASSIGNED_PENDING_REVIEW,
        ("reviewers_assigned", "is_not_request_owner"),
    ),
    Transition(
        "appraisal",
        REVIEWER_ASSIGNED_PENDING_REVIEW,
        "forward",
        APPROVING_AUTHORITY,
        PENDING_NEXT_AUTHORITY,
        ("current_actor_is_authority", "is_not_request_owner", "configured_next_authority_exists"),
    ),
    Transition(
        "appraisal",
        PENDING_NEXT_AUTHORITY,
        "forward",
        APPROVING_AUTHORITY,
        PENDING_NEXT_AUTHORITY,
        ("current_actor_is_authority", "is_not_request_owner", "configured_next_authority_exists"),
    ),
    Transition(
        "appraisal",
        REVIEWER_ASSIGNED_PENDING_REVIEW,
        "finalize",
        APPROVING_AUTHORITY,
        FINALIZED_ARCHIVED_CLOSED,
        ("current_actor_is_authority", "is_not_request_owner", "final_authority"),
    ),
    Transition(
        "appraisal",
        PENDING_NEXT_AUTHORITY,
        "finalize",
        APPROVING_AUTHORITY,
        FINALIZED_ARCHIVED_CLOSED,
        ("current_actor_is_authority", "is_not_request_owner", "final_authority"),
    ),
)

for _resource in ("ltc", "cpda"):
    _required = (
        ("prescribed_form", "documentation_and_eligibility")
        if _resource == "ltc"
        else ("purpose_and_amount", "supporting_documents")
    )
    _approved = APPROVED_LTC_CLAIM if _resource == "ltc" else APPROVED_CPDA_CLAIM
    TRANSITIONS += (
        Transition(_resource, DRAFT, "submit", EMPLOYEE, AWAITING_HR_VERIFICATION, _required),
        Transition(
            _resource,
            AWAITING_HR_VERIFICATION,
            "verify",
            HR_ADMINISTRATOR,
            PENDING_CURRENT_AUTHORITY,
            ("hr_verification_complete", "route_exists", "is_not_request_owner"),
        ),
        *(
            Transition(
                _resource,
                state,
                "approve",
                APPROVING_AUTHORITY,
                _approved,
                ("current_actor_is_authority", "is_not_request_owner", "final_authority"),
            )
            for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
        ),
        *(
            Transition(
                _resource,
                state,
                "reject",
                APPROVING_AUTHORITY,
                REJECTED,
                ("current_actor_is_authority", "is_not_request_owner"),
            )
            for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
        ),
        *(
            Transition(
                _resource,
                state,
                "forward",
                APPROVING_AUTHORITY,
                PENDING_NEXT_AUTHORITY,
                (
                    "current_actor_is_authority",
                    "is_not_request_owner",
                    "configured_next_authority_exists",
                ),
            )
            for state in (PENDING_CURRENT_AUTHORITY, PENDING_NEXT_AUTHORITY)
        ),
        Transition(
            _resource,
            _approved,
            "process",
            ACCOUNTANT,
            PROCESSED_FINANCIAL_STATUS_RECORDED,
            ("accountant_processing_details_valid",),
        ),
    )

_INDEX: dict[tuple[str, str, str, str], Transition] = {}
for _transition in TRANSITIONS:
    _key = (_transition.resource, _transition.source, _transition.event, _transition.actor)
    if _key in _INDEX:
        raise RuntimeError(f"Duplicate HR-EIS transition: {_key!r}")
    _INDEX[_key] = _transition


def resolve(resource: str, state: str, event: str, actor: str) -> Transition:
    transition = _INDEX.get((resource, state, event, actor))
    if transition is not None:
        return transition
    if any(t.resource == resource and t.source == state and t.event == event for t in TRANSITIONS):
        raise ActorNotAllowed(actor, resource, event)
    raise InvalidTransition(resource, state, event)


def apply(
    resource: str, state: str, event: str, actor: str, facts: dict[str, bool] | None = None
) -> str:
    transition = resolve(resource, state, event, actor)
    facts = facts or {}
    for guard in transition.guards:
        if facts.get(guard) is not True:
            raise GuardFailed(guard)
    return transition.target
