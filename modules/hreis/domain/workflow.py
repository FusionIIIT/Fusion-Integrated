"""Declarative HR-EIS workflow edges from the live BW-HR / CW-HR specifications.

No configuration value, approval route, leave entitlement or external finance
status is inferred here. Services must derive guard facts from trusted,
effective-dated policy and the current IAM role, not from user-submitted flags.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

LEAVE = "leave"
APPRAISAL = "appraisal"
LTC = "ltc"
CPDA = "cpda"
FAMILIES = frozenset({LEAVE, APPRAISAL, LTC, CPDA})

EMPLOYEE = "employee"
HR_ADMINISTRATOR = "hr_administrator"
AUTHORITY = "approving_authority"
ACCOUNTANT = "accountant"

DRAFT = "draft"
NOT_SUBMITTED = "not_submitted"
SUBMITTED = "submitted"
AWAITING_HR_VERIFICATION = "awaiting_hr_verification"
PENDING_AUTHORITY = "pending_authority"
PENDING_REVIEW = "pending_review"
PENDING_NEXT_APPRAISAL_AUTHORITY = "pending_next_appraisal_authority"
APPROVED = "approved"
REJECTED = "rejected"
FINALIZED = "finalized"
FINANCIAL_PROCESSING_RECORDED = "financial_processing_recorded"

TERMINAL_STATES = {
    LEAVE: frozenset({APPROVED, REJECTED}),
    APPRAISAL: frozenset({FINALIZED}),
    LTC: frozenset({REJECTED, FINANCIAL_PROCESSING_RECORDED}),
    CPDA: frozenset({REJECTED, FINANCIAL_PROCESSING_RECORDED}),
}


class WorkflowError(ValueError):
    """An undeclared, unauthorized or unverified state change."""


class UnknownWorkflow(WorkflowError):
    """The requested workflow family is outside the live specification."""


class InvalidTransition(WorkflowError):
    """There is no declared edge for this source state and event."""


class ActorNotAllowed(WorkflowError):
    """The supplied active role cannot perform the declared edge."""


class GuardFailed(WorkflowError):
    """A required, server-derived precondition was not demonstrated."""

    def __init__(self, guard: str):
        super().__init__(f"Required condition is not satisfied: {guard}.")
        self.guard = guard


@dataclass(frozen=True)
class Transition:
    family: str
    source: str
    event: str
    target: str
    actor: str
    guards: tuple[str, ...]
    specification: str
    effect: str = ""


def _t(
    family: str,
    source: str,
    event: str,
    target: str,
    actor: str,
    specification: str,
    *guards: str,
    effect: str = "",
) -> Transition:
    return Transition(family, source, event, target, actor, guards, specification, effect)


TRANSITIONS: tuple[Transition, ...] = (
    # CW-HR-01; BW-HR-01/02/03.
    _t(
        LEAVE,
        DRAFT,
        "submit",
        PENDING_AUTHORITY,
        EMPLOYEE,
        "CW-HR-01",
        "supported_leave_type",
        "required_fields",
        "balance_valid",
        "eligibility_valid",
        "route_configured",
    ),
    _t(
        LEAVE,
        PENDING_AUTHORITY,
        "approve",
        APPROVED,
        AUTHORITY,
        "BW-HR-01",
        "current_authority",
        "balance_valid",
        effect="post_leave_ledger",
    ),
    _t(LEAVE, PENDING_AUTHORITY, "reject", REJECTED, AUTHORITY, "BW-HR-02", "current_authority"),
    _t(
        LEAVE,
        PENDING_AUTHORITY,
        "forward",
        PENDING_AUTHORITY,
        AUTHORITY,
        "BW-HR-03",
        "current_authority",
        "next_authority_exists",
        effect="advance_route_step",
    ),
    # CW-HR-02; BW-HR-04/05. No rejection or return edge is specified.
    _t(
        APPRAISAL,
        NOT_SUBMITTED,
        "submit",
        SUBMITTED,
        EMPLOYEE,
        "CW-HR-02",
        "submission_window_open",
    ),
    _t(
        APPRAISAL,
        SUBMITTED,
        "assign_reviewers",
        PENDING_REVIEW,
        HR_ADMINISTRATOR,
        "CW-HR-02",
        "reviewers_assigned",
    ),
    _t(
        APPRAISAL,
        PENDING_REVIEW,
        "forward",
        PENDING_NEXT_APPRAISAL_AUTHORITY,
        AUTHORITY,
        "BW-HR-05",
        "current_authority",
        "not_final_authority",
        effect="advance_route_step",
    ),
    _t(
        APPRAISAL,
        PENDING_REVIEW,
        "finalize",
        FINALIZED,
        AUTHORITY,
        "BW-HR-04",
        "current_authority",
        "final_authority",
        effect="archive_appraisal",
    ),
    _t(
        APPRAISAL,
        PENDING_NEXT_APPRAISAL_AUTHORITY,
        "forward",
        PENDING_NEXT_APPRAISAL_AUTHORITY,
        AUTHORITY,
        "BW-HR-05",
        "current_authority",
        "not_final_authority",
        effect="advance_route_step",
    ),
    _t(
        APPRAISAL,
        PENDING_NEXT_APPRAISAL_AUTHORITY,
        "finalize",
        FINALIZED,
        AUTHORITY,
        "BW-HR-05",
        "current_authority",
        "final_authority",
        effect="archive_appraisal",
    ),
    # CW-HR-03; BW-HR-06/07/08/09.
    _t(
        LTC,
        DRAFT,
        "submit",
        AWAITING_HR_VERIFICATION,
        EMPLOYEE,
        "CW-HR-03",
        "prescribed_form_present",
    ),
    _t(
        LTC,
        AWAITING_HR_VERIFICATION,
        "verify",
        PENDING_AUTHORITY,
        HR_ADMINISTRATOR,
        "CW-HR-03",
        "documents_verified",
        "eligibility_verified",
        "route_configured",
    ),
    _t(LTC, PENDING_AUTHORITY, "approve", APPROVED, AUTHORITY, "BW-HR-06", "current_authority"),
    _t(LTC, PENDING_AUTHORITY, "reject", REJECTED, AUTHORITY, "BW-HR-08", "current_authority"),
    _t(
        LTC,
        PENDING_AUTHORITY,
        "forward",
        PENDING_AUTHORITY,
        AUTHORITY,
        "BW-HR-09",
        "current_authority",
        "next_authority_exists",
        effect="advance_route_step",
    ),
    _t(
        LTC,
        APPROVED,
        "record_financial_processing",
        FINANCIAL_PROCESSING_RECORDED,
        ACCOUNTANT,
        "CW-HR-03",
        "financial_correctness_verified",
        "processing_status_recorded",
    ),
    # CW-HR-04; BW-HR-10/11/12/13.
    _t(
        CPDA,
        DRAFT,
        "submit",
        AWAITING_HR_VERIFICATION,
        EMPLOYEE,
        "CW-HR-04",
        "purpose_present",
        "amount_present",
        "documents_present",
    ),
    _t(
        CPDA,
        AWAITING_HR_VERIFICATION,
        "verify",
        PENDING_AUTHORITY,
        HR_ADMINISTRATOR,
        "CW-HR-04",
        "verification_passed",
        "route_configured",
    ),
    _t(CPDA, PENDING_AUTHORITY, "approve", APPROVED, AUTHORITY, "BW-HR-10", "current_authority"),
    _t(CPDA, PENDING_AUTHORITY, "reject", REJECTED, AUTHORITY, "BW-HR-12", "current_authority"),
    _t(
        CPDA,
        PENDING_AUTHORITY,
        "forward",
        PENDING_AUTHORITY,
        AUTHORITY,
        "BW-HR-13",
        "current_authority",
        "next_authority_exists",
        effect="advance_route_step",
    ),
    _t(
        CPDA,
        APPROVED,
        "record_financial_processing",
        FINANCIAL_PROCESSING_RECORDED,
        ACCOUNTANT,
        "CW-HR-04",
        "financial_correctness_verified",
        "disbursement_details_recorded",
    ),
)

_INDEX = {(t.family, t.source, t.event): t for t in TRANSITIONS}
if len(_INDEX) != len(TRANSITIONS):
    raise RuntimeError("Duplicate HR-EIS transition definition.")


def resolve(
    family: str, source: str, event: str, actor: str, *, guard_results: Mapping[str, bool]
) -> Transition:
    """Resolve one legal move, denying any missing/false guard.

    Services own the policy evaluation and current-role/step lookup. In
    particular, clients must never supply guard_results directly.
    """
    if family not in FAMILIES:
        raise UnknownWorkflow(f"Unknown HR request family: {family!r}.")
    transition = _INDEX.get((family, source, event))
    if transition is None:
        raise InvalidTransition(f"{family} request in {source!r} cannot perform {event!r}.")
    if actor != transition.actor:
        raise ActorNotAllowed(f"{actor!r} cannot perform {event!r} on {family} requests.")
    for guard in transition.guards:
        if guard_results.get(guard) is not True:
            raise GuardFailed(guard)
    return transition


def allowed_events(family: str, source: str, actor: str) -> frozenset[str]:
    if family not in FAMILIES:
        raise UnknownWorkflow(f"Unknown HR request family: {family!r}.")
    return frozenset(
        t.event for t in TRANSITIONS if (t.family, t.source, t.actor) == (family, source, actor)
    )


def is_terminal(family: str, source: str) -> bool:
    if family not in FAMILIES:
        raise UnknownWorkflow(f"Unknown HR request family: {family!r}.")
    return source in TERMINAL_STATES[family]
