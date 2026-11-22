"""RSPC Declarative State Machines (Pure Python).

Enforces structural validity of status transitions. Illegal transitions raise DomainTransitionError.
"""

from __future__ import annotations

from modules.rspc.domain.entities import ProjectStatus, ProposalStatus


class DomainTransitionError(ValueError):
    """Raised when an illegal state machine transition is attempted."""


class ProposalStateMachine:
    """Transition table: (current_status, event, role) -> new_status."""

    TRANSITIONS = {
        (ProposalStatus.DRAFT, "submit", "faculty"): ProposalStatus.SUBMITTED_HOD,
        (ProposalStatus.SUBMITTED_HOD, "endorse", "hod"): ProposalStatus.ENDORSED_HOD,
        (
            ProposalStatus.SUBMITTED_HOD,
            "request_revision",
            "hod",
        ): ProposalStatus.REVISION_REQUESTED,
        (ProposalStatus.REVISION_REQUESTED, "resubmit", "faculty"): ProposalStatus.SUBMITTED_HOD,
        (ProposalStatus.SUBMITTED_HOD, "reject", "hod"): ProposalStatus.DEPT_NOT_RECOMMENDED,
        (ProposalStatus.ENDORSED_HOD, "approve", "dean"): ProposalStatus.APPROVED_DEAN,
        (ProposalStatus.ENDORSED_HOD, "reject", "dean"): ProposalStatus.DEAN_NOT_APPROVED,
    }

    @classmethod
    def transition(
        cls, current_status: str, event: str, actor_role: str, pi_user_id: int, actor_user_id: int
    ) -> str:
        # Guard: BR-RSPC-004 Dual Role Approval Prohibition (PI cannot approve their own proposal)
        if event in ("endorse", "approve") and pi_user_id == actor_user_id:
            raise DomainTransitionError(
                "Conflict of interest: PI cannot endorse or approve their own proposal."
            )

        key = (current_status, event, actor_role.lower())
        if key not in cls.TRANSITIONS:
            raise DomainTransitionError(
                f"Illegal transition: Cannot '{event}' from '{current_status}' "
                f"by role '{actor_role}'."
            )
        return cls.TRANSITIONS[key]


class ProjectLifecycleStateMachine:
    """Transition table: (current_status, event, role) -> new_status."""

    TRANSITIONS = {
        (ProjectStatus.SANCTIONED, "activate", "admin"): ProjectStatus.ACTIVE,
        (ProjectStatus.SANCTIONED, "activate", "dean"): ProjectStatus.ACTIVE,
        (ProjectStatus.ACTIVE, "request_extension", "faculty"): ProjectStatus.EXTENSION_REQUESTED,
        (ProjectStatus.EXTENSION_REQUESTED, "approve_extension", "dean"): ProjectStatus.ACTIVE,
        (ProjectStatus.EXTENSION_REQUESTED, "reject_extension", "dean"): ProjectStatus.ACTIVE,
        (ProjectStatus.ACTIVE, "request_closure", "faculty"): ProjectStatus.CLOSURE_PENDING,
        (ProjectStatus.CLOSURE_PENDING, "approve_closure", "dean"): ProjectStatus.CLOSED,
        (ProjectStatus.ACTIVE, "terminate", "dean"): ProjectStatus.TERMINATED,
    }

    @classmethod
    def transition(cls, current_status: str, event: str, actor_role: str) -> str:
        key = (current_status, event, actor_role.lower())
        if key not in cls.TRANSITIONS:
            raise DomainTransitionError(
                f"Illegal transition: Cannot '{event}' from '{current_status}' "
                f"by role '{actor_role}'."
            )
        return cls.TRANSITIONS[key]
