"""PMS State Machine and Lifecycle Governance.

Pure Python: no Django, DRF or Celery imports.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from .errors import InvalidTransitionError, WithdrawalNotAllowedError


class PatentApplicationStatus(StrEnum):
    # Initial & Review
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    NEEDS_REVISION = "needs_revision"
    RESUBMITTED = "resubmitted"
    REJECTED = "rejected"
    EXPIRED = "expired"

    # Appeal Path
    APPEAL_SUBMITTED = "appeal_submitted"
    REJECTION_UPHELD = "rejection_upheld"
    REMANDED_FOR_AMENDMENT = "remanded_for_amendment"
    DECISION_MODIFIED = "decision_modified"

    # Attorney & Budget
    ASSIGNMENT_OFFERED = "assignment_offered"
    ATTORNEY_ASSIGNED = "attorney_assigned"
    PENDING_REVIEW = "pending_review"
    BUDGET_APPROVED = "budget_approved"
    BUDGET_REJECTED = "budget_rejected"
    ESCALATED = "escalated"
    ESCALATION_TRACKED = "escalation_tracked"

    # Filing & Office Actions
    PRE_FILING_SATISFIED = "pre_filing_satisfied"
    FILED = "filed"
    OFFICE_ACTION_RECORDED = "office_action_recorded"
    AWAITING_APPLICANT_APPROVAL = "awaiting_applicant_approval"
    APPLICANT_APPROVED = "applicant_approved"
    RESPONSE_READY = "response_ready"
    RESPONSE_SUBMITTED = "response_submitted"

    # Post-Grant Maintenance
    GRANTED = "granted"
    RENEWAL_DECISION_REQUESTED = "renewal_decision_requested"
    RENEWAL_APPROVED = "renewal_approved"
    DO_NOT_RENEW = "do_not_renew"
    RENEWED = "renewed"

    # Withdrawal
    WITHDRAWN = "withdrawn"


#: Pre-filing states eligible for withdrawal (BR-PMS-067, BR-PMS-068, CW-PMS-05)
WITHDRAWAL_ELIGIBLE_STATES: frozenset[PatentApplicationStatus] = frozenset(
    {
        PatentApplicationStatus.SUBMITTED,
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.NEEDS_REVISION,
        PatentApplicationStatus.RESUBMITTED,
        PatentApplicationStatus.REJECTED,
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        PatentApplicationStatus.PENDING_REVIEW,
        PatentApplicationStatus.BUDGET_APPROVED,
        PatentApplicationStatus.BUDGET_REJECTED,
        PatentApplicationStatus.ESCALATED,
        PatentApplicationStatus.ESCALATION_TRACKED,
        PatentApplicationStatus.PRE_FILING_SATISFIED,
    }
)

#: Terminal states
TERMINAL_STATES: frozenset[PatentApplicationStatus] = frozenset(
    {
        PatentApplicationStatus.WITHDRAWN,
        PatentApplicationStatus.EXPIRED,
        PatentApplicationStatus.REJECTION_UPHELD,
        PatentApplicationStatus.DO_NOT_RENEW,
    }
)


@dataclass(frozen=True)
class Transition:
    from_status: PatentApplicationStatus
    to_status: PatentApplicationStatus
    actor_role: str
    uc_id: str
    permission: str
    guard_description: str = ""


# Authoritative state transitions grounded in BW-PMS-01 through BW-PMS-16 and CW-PMS-01 through CW-PMS-05
TRANSITIONS: tuple[Transition, ...] = (
    # BW-PMS-01: Initial Review Approval Path
    Transition(
        PatentApplicationStatus.DRAFT,
        PatentApplicationStatus.SUBMITTED,
        actor_role="Applicant",
        uc_id="UC-PMS-001",
        permission="pms.application.create",
        guard_description="Completeness and document validation",
    ),
    Transition(
        PatentApplicationStatus.SUBMITTED,
        PatentApplicationStatus.UNDER_REVIEW,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-007",
        permission="pms.application.assign_director",
        guard_description="Eligible Director selected without conflict",
    ),
    Transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.APPROVED,
        actor_role="Director",
        uc_id="UC-PMS-008",
        permission="pms.application.review",
        guard_description="Decision = Approve, justification >= 50 chars",
    ),
    # BW-PMS-02: Revision and Re-Approval Path
    Transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.NEEDS_REVISION,
        actor_role="Director",
        uc_id="UC-PMS-008",
        permission="pms.application.review",
        guard_description="Decision = Needs Revision, justification >= 50 chars",
    ),
    Transition(
        PatentApplicationStatus.NEEDS_REVISION,
        PatentApplicationStatus.RESUBMITTED,
        actor_role="Applicant",
        uc_id="UC-PMS-005",
        permission="pms.application.revise",
        guard_description="Within 60 days, addresses feedback",
    ),
    Transition(
        PatentApplicationStatus.RESUBMITTED,
        PatentApplicationStatus.UNDER_REVIEW,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-007",
        permission="pms.application.assign_director",
        guard_description="Valid assignment/reassignment",
    ),
    # Overdue revision expiration (BR-PMS-038)
    Transition(
        PatentApplicationStatus.NEEDS_REVISION,
        PatentApplicationStatus.EXPIRED,
        actor_role="System",
        uc_id="UC-PMS-016",
        permission="pms.application.auto_expire",
        guard_description="Revision deadline exceeded",
    ),
    Transition(
        PatentApplicationStatus.REJECTED,
        PatentApplicationStatus.EXPIRED,
        actor_role="System",
        uc_id="UC-PMS-016",
        permission="pms.application.auto_expire",
        guard_description="Revision deadline exceeded without resubmission or appeal",
    ),
    # Rejection and Revision from Rejected (BR-PMS-034)
    Transition(
        PatentApplicationStatus.UNDER_REVIEW,
        PatentApplicationStatus.REJECTED,
        actor_role="Director",
        uc_id="UC-PMS-008",
        permission="pms.application.review",
        guard_description="Decision = Reject, justification >= 50 chars",
    ),
    Transition(
        PatentApplicationStatus.REJECTED,
        PatentApplicationStatus.RESUBMITTED,
        actor_role="Applicant",
        uc_id="UC-PMS-005",
        permission="pms.application.revise",
        guard_description="Revision within 60 days addressing feedback",
    ),
    # BW-PMS-03, 04, 05: Appeal Paths
    Transition(
        PatentApplicationStatus.REJECTED,
        PatentApplicationStatus.APPEAL_SUBMITTED,
        actor_role="Applicant",
        uc_id="UC-PMS-022",
        permission="pms.application.appeal",
        guard_description="Appeal filed within allowed period with grounds and justification",
    ),
    Transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.REMANDED_FOR_AMENDMENT,
        actor_role="Director",
        uc_id="UC-PMS-023",
        permission="pms.application.review_appeal",
        guard_description="Outcome = Remand for Amendment",
    ),
    Transition(
        PatentApplicationStatus.REMANDED_FOR_AMENDMENT,
        PatentApplicationStatus.RESUBMITTED,
        actor_role="Applicant",
        uc_id="UC-PMS-005",
        permission="pms.application.revise",
        guard_description="Amended resubmission following remand",
    ),
    Transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.REJECTION_UPHELD,
        actor_role="Director",
        uc_id="UC-PMS-023",
        permission="pms.application.review_appeal",
        guard_description="Outcome = Uphold Rejection",
    ),
    Transition(
        PatentApplicationStatus.APPEAL_SUBMITTED,
        PatentApplicationStatus.DECISION_MODIFIED,
        actor_role="Director",
        uc_id="UC-PMS-023",
        permission="pms.application.review_appeal",
        guard_description="Outcome = Modify Decision",
    ),
    Transition(
        PatentApplicationStatus.DECISION_MODIFIED,
        PatentApplicationStatus.APPROVED,
        actor_role="Director",
        uc_id="UC-PMS-023",
        permission="pms.application.review_appeal",
        guard_description="Modified to Approved",
    ),
    # BW-PMS-06, 07: Attorney Assignment Paths
    Transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-010",
        permission="pms.attorney.assign",
        guard_description="Assigned from approved panel with expertise and workload balance",
    ),
    Transition(
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        actor_role="Attorney",
        uc_id="UC-PMS-011",
        permission="pms.attorney.respond_assignment",
        guard_description="Outcome = Accept",
    ),
    Transition(
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        PatentApplicationStatus.PENDING_REVIEW,
        actor_role="Attorney",
        uc_id="UC-PMS-011",
        permission="pms.attorney.respond_assignment",
        guard_description="Outcome = Decline",
    ),
    Transition(
        PatentApplicationStatus.PENDING_REVIEW,
        PatentApplicationStatus.ASSIGNMENT_OFFERED,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-010",
        permission="pms.attorney.assign",
        guard_description="Reassignment to another approved panel attorney",
    ),
    # BW-PMS-08, 09, 10: Budget Paths
    Transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.BUDGET_APPROVED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Decision = Approve, within threshold limit and available",
    ),
    Transition(
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        PatentApplicationStatus.BUDGET_APPROVED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Decision = Approve, within threshold limit and available",
    ),
    Transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.BUDGET_REJECTED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Decision = Reject",
    ),
    Transition(
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        PatentApplicationStatus.BUDGET_REJECTED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Decision = Reject",
    ),
    Transition(
        PatentApplicationStatus.APPROVED,
        PatentApplicationStatus.ESCALATED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Total cost exceeds threshold limit",
    ),
    Transition(
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        PatentApplicationStatus.ESCALATED,
        actor_role="Director",
        uc_id="UC-PMS-009",
        permission="pms.budget.review",
        guard_description="Total cost exceeds threshold limit",
    ),
    Transition(
        PatentApplicationStatus.ESCALATED,
        PatentApplicationStatus.ESCALATION_TRACKED,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-027",
        permission="pms.workflow.monitor",
        guard_description="PCC_ADMIN logs and routes escalation to higher authority",
    ),
    Transition(
        PatentApplicationStatus.ESCALATION_TRACKED,
        PatentApplicationStatus.BUDGET_APPROVED,
        actor_role="PCC_ADMIN",
        uc_id="UC-PMS-027",
        permission="pms.workflow.monitor",
        guard_description="Higher authority approval recorded",
    ),
    # Pre-filing satisfied & BW-PMS-11 External Filing
    Transition(
        PatentApplicationStatus.BUDGET_APPROVED,
        PatentApplicationStatus.PRE_FILING_SATISFIED,
        actor_role="Attorney",
        uc_id="UC-PMS-013",
        permission="pms.filing.record",
        guard_description="Approvals, budget, inventor agreements and format validation complete",
    ),
    Transition(
        PatentApplicationStatus.ATTORNEY_ASSIGNED,
        PatentApplicationStatus.PRE_FILING_SATISFIED,
        actor_role="Attorney",
        uc_id="UC-PMS-013",
        permission="pms.filing.record",
        guard_description="Approvals, budget, inventor agreements and format validation complete",
    ),
    Transition(
        PatentApplicationStatus.PRE_FILING_SATISFIED,
        PatentApplicationStatus.FILED,
        actor_role="Attorney",
        uc_id="UC-PMS-013",
        permission="pms.filing.record",
        guard_description="Filing reference and confirmation recorded",
    ),
    Transition(
        PatentApplicationStatus.BUDGET_APPROVED,
        PatentApplicationStatus.FILED,
        actor_role="Attorney",
        uc_id="UC-PMS-013",
        permission="pms.filing.record",
        guard_description="Direct filing when preconditions satisfied",
    ),
    # BW-PMS-12, 13, CW-PMS-03: Office Action Responses
    Transition(
        PatentApplicationStatus.FILED,
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        actor_role="Attorney",
        uc_id="UC-PMS-014",
        permission="pms.office_action.record",
        guard_description="Office action received and logged",
    ),
    Transition(
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL,
        actor_role="Attorney",
        uc_id="UC-PMS-015",
        permission="pms.office_action.respond",
        guard_description="Draft response prepared; applicant review required",
    ),
    Transition(
        PatentApplicationStatus.AWAITING_APPLICANT_APPROVAL,
        PatentApplicationStatus.APPLICANT_APPROVED,
        actor_role="Applicant",
        uc_id="UC-PMS-029",
        permission="pms.office_action.review",
        guard_description="Applicant approves response",
    ),
    Transition(
        PatentApplicationStatus.APPLICANT_APPROVED,
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        actor_role="Attorney",
        uc_id="UC-PMS-015",
        permission="pms.office_action.respond",
        guard_description="Final response submitted within deadline",
    ),
    Transition(
        PatentApplicationStatus.OFFICE_ACTION_RECORDED,
        PatentApplicationStatus.RESPONSE_READY,
        actor_role="Attorney",
        uc_id="UC-PMS-015",
        permission="pms.office_action.respond",
        guard_description="Applicant review not required",
    ),
    Transition(
        PatentApplicationStatus.RESPONSE_READY,
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        actor_role="Attorney",
        uc_id="UC-PMS-015",
        permission="pms.office_action.respond",
        guard_description="Response submitted within deadline",
    ),
    Transition(
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        PatentApplicationStatus.FILED,
        actor_role="Attorney",
        uc_id="UC-PMS-014",
        permission="pms.office_action.record",
        guard_description="Returns to active post-filing tracking",
    ),
    # Grant & BW-PMS-14, 15, CW-PMS-04: Maintenance Cycles
    Transition(
        PatentApplicationStatus.FILED,
        PatentApplicationStatus.GRANTED,
        actor_role="Attorney",
        uc_id="UC-PMS-014",
        permission="pms.office_action.record",
        guard_description="Grant recorded by Attorney",
    ),
    Transition(
        PatentApplicationStatus.RESPONSE_SUBMITTED,
        PatentApplicationStatus.GRANTED,
        actor_role="Attorney",
        uc_id="UC-PMS-014",
        permission="pms.office_action.record",
        guard_description="Grant recorded following office action resolution",
    ),
    Transition(
        PatentApplicationStatus.GRANTED,
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        actor_role="Attorney",
        uc_id="UC-PMS-017",
        permission="pms.maintenance.manage",
        guard_description="Maintenance fee renewal decision requested",
    ),
    Transition(
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        PatentApplicationStatus.RENEWAL_APPROVED,
        actor_role="Director",
        uc_id="UC-PMS-018",
        permission="pms.maintenance.decide",
        guard_description="Director decides Renew",
    ),
    Transition(
        PatentApplicationStatus.RENEWAL_APPROVED,
        PatentApplicationStatus.RENEWED,
        actor_role="Attorney",
        uc_id="UC-PMS-017",
        permission="pms.maintenance.manage",
        guard_description="Maintenance transaction recorded; next cycle scheduled",
    ),
    Transition(
        PatentApplicationStatus.RENEWED,
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        actor_role="Attorney",
        uc_id="UC-PMS-017",
        permission="pms.maintenance.manage",
        guard_description="Subsequent renewal cycle due",
    ),
    Transition(
        PatentApplicationStatus.RENEWAL_DECISION_REQUESTED,
        PatentApplicationStatus.DO_NOT_RENEW,
        actor_role="Director",
        uc_id="UC-PMS-018",
        permission="pms.maintenance.decide",
        guard_description="Director decides Do Not Renew",
    ),
    # BW-PMS-16 & CW-PMS-05: Pre-Filing Withdrawal
    *(
        Transition(
            state,
            PatentApplicationStatus.WITHDRAWN,
            actor_role="Applicant",
            uc_id="UC-PMS-006",
            permission="pms.application.withdraw",
            guard_description="Before filing, reason provided, co-inventor consent recorded",
        )
        for state in WITHDRAWAL_ELIGIBLE_STATES
    ),
)


def get_transitions(from_status: PatentApplicationStatus) -> list[Transition]:
    """Return all valid outgoing transitions from a given status."""
    return [t for t in TRANSITIONS if t.from_status == from_status]


def validate_transition(
    current_status: PatentApplicationStatus | str,
    target_status: PatentApplicationStatus | str,
    actor_role: str | None = None,
    *,
    reason: str = "",
    has_coinventor_consent: bool = True,
) -> Transition:
    """Validate that moving from current_status to target_status is permitted.

    Raises InvalidTransitionError or WithdrawalNotAllowedError if disallowed.
    """
    try:
        curr = PatentApplicationStatus(current_status)
        target = PatentApplicationStatus(target_status)
    except ValueError as exc:
        raise InvalidTransitionError(f"Invalid status value: {exc}") from exc

    if target == PatentApplicationStatus.WITHDRAWN:
        if curr not in WITHDRAWAL_ELIGIBLE_STATES:
            raise WithdrawalNotAllowedError(
                f"Withdrawal is not permitted from status '{curr.value}' (only allowed before filing)."
            )
        if not reason or not reason.strip():
            raise WithdrawalNotAllowedError("A withdrawal reason is required.")
        if not has_coinventor_consent:
            raise WithdrawalNotAllowedError("All co-inventors must consent to withdrawal.")

    matching = [t for t in TRANSITIONS if t.from_status == curr and t.to_status == target]

    if not matching:
        raise InvalidTransitionError(
            f"Cannot transition application from '{curr.value}' to '{target.value}'."
        )

    if actor_role:
        role_matching = [
            t for t in matching if t.actor_role == actor_role or t.actor_role == "System"
        ]
        if not role_matching:
            raise InvalidTransitionError(
                f"Role '{actor_role}' is not authorized to transition from '{curr.value}' to '{target.value}'."
            )
        return role_matching[0]

    return matching[0]
