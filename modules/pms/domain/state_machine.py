from dataclasses import dataclass
from typing import ClassVar

from modules.pms.models.application import ApplicationStatus


class IllegalTransitionError(ValueError):
    """Raised when an invalid state transition is attempted."""


@dataclass(frozen=True)
class TransitionRule:
    from_status: str
    event: str
    allowed_roles: tuple[str, ...]
    to_status: str


class PatentStateMachine:
    """Declarative, deterministic finite state machine for Patent Application lifecycle.
    
    In accordance with §3.3, illegal transitions are inexpressible and rejected.
    """

    TRANSITIONS: ClassVar[tuple[TransitionRule, ...]] = (
        # Draft -> Submitted
        TransitionRule(
            from_status=ApplicationStatus.DRAFT,
            event="SUBMIT",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.SUBMITTED,
        ),
        # Submitted -> Under Review (Director / Scrutiny assigned)
        TransitionRule(
            from_status=ApplicationStatus.SUBMITTED,
            event="ASSIGN_DIRECTOR",
            allowed_roles=("pms_coordinator", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.UNDER_REVIEW,
        ),
        # Under Review -> Needs Revision
        TransitionRule(
            from_status=ApplicationStatus.UNDER_REVIEW,
            event="REQUEST_REVISION",
            allowed_roles=("director", "Dean R&D", "pms_reviewer", "pcc_admin"),
            to_status=ApplicationStatus.NEEDS_REVISION,
        ),
        # Needs Revision -> Under Review (Resubmission by applicant)
        TransitionRule(
            from_status=ApplicationStatus.NEEDS_REVISION,
            event="RESUBMIT",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.UNDER_REVIEW,
        ),
        # Under Review -> Approved
        TransitionRule(
            from_status=ApplicationStatus.UNDER_REVIEW,
            event="APPROVE",
            allowed_roles=("director", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.APPROVED,
        ),
        # Under Review -> Rejected
        TransitionRule(
            from_status=ApplicationStatus.UNDER_REVIEW,
            event="REJECT",
            allowed_roles=("director", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.REJECTED,
        ),
        # Rejected -> Appealed
        TransitionRule(
            from_status=ApplicationStatus.REJECTED,
            event="APPEAL",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.APPEALED,
        ),
        # Appealed -> Under Review (Remand)
        TransitionRule(
            from_status=ApplicationStatus.APPEALED,
            event="REMAND",
            allowed_roles=("director", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.UNDER_REVIEW,
        ),
        # Appealed -> Rejected (Upheld)
        TransitionRule(
            from_status=ApplicationStatus.APPEALED,
            event="UPHOLD_REJECTION",
            allowed_roles=("director", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.REJECTED,
        ),
        # Approved -> Attorney Assigned
        TransitionRule(
            from_status=ApplicationStatus.APPROVED,
            event="ASSIGN_ATTORNEY",
            allowed_roles=("pms_coordinator", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.ATTORNEY_ASSIGNED,
        ),
        # Attorney Assigned -> Filing in Progress (Accepted by Attorney)
        TransitionRule(
            from_status=ApplicationStatus.ATTORNEY_ASSIGNED,
            event="ACCEPT_ASSIGNMENT",
            allowed_roles=("pms_attorney", "attorney"),
            to_status=ApplicationStatus.FILING_IN_PROGRESS,
        ),
        # Attorney Assigned -> Attorney Assigned (Declined and reassigned)
        TransitionRule(
            from_status=ApplicationStatus.ATTORNEY_ASSIGNED,
            event="DECLINE_ASSIGNMENT",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator"),
            to_status=ApplicationStatus.ATTORNEY_ASSIGNED,
        ),
        # Filing in Progress -> Filed (External Patent Office Filing)
        TransitionRule(
            from_status=ApplicationStatus.FILING_IN_PROGRESS,
            event="RECORD_FILING",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator", "pcc_admin"),
            to_status=ApplicationStatus.FILED,
        ),
        # Filed -> FER Received
        TransitionRule(
            from_status=ApplicationStatus.FILED,
            event="RECEIVE_FER",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator"),
            to_status=ApplicationStatus.FER_RECEIVED,
        ),
        # FER Received -> FER Responded
        TransitionRule(
            from_status=ApplicationStatus.FER_RECEIVED,
            event="SUBMIT_RESPONSE",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator"),
            to_status=ApplicationStatus.FER_RESPONDED,
        ),
        # FER Responded -> Granted
        TransitionRule(
            from_status=ApplicationStatus.FER_RESPONDED,
            event="GRANT",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator", "Dean R&D", "pcc_admin"),
            to_status=ApplicationStatus.GRANTED,
        ),
        # FER Responded -> Refused
        TransitionRule(
            from_status=ApplicationStatus.FER_RESPONDED,
            event="REFUSE",
            allowed_roles=("pms_attorney", "attorney", "pms_coordinator", "pcc_admin"),
            to_status=ApplicationStatus.REFUSED,
        ),
        # Granted -> Maintenance (Annuity Tracking)
        TransitionRule(
            from_status=ApplicationStatus.GRANTED,
            event="START_MAINTENANCE",
            allowed_roles=("system", "pms_coordinator", "pcc_admin"),
            to_status=ApplicationStatus.MAINTENANCE,
        ),
        # Maintenance -> Expired
        TransitionRule(
            from_status=ApplicationStatus.MAINTENANCE,
            event="EXPIRE",
            allowed_roles=("system", "pms_coordinator", "pcc_admin"),
            to_status=ApplicationStatus.EXPIRED,
        ),
        # Pre-filing Withdrawals (BW-PMS-16)
        TransitionRule(
            from_status=ApplicationStatus.DRAFT,
            event="WITHDRAW",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.WITHDRAWN,
        ),
        TransitionRule(
            from_status=ApplicationStatus.SUBMITTED,
            event="WITHDRAW",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.WITHDRAWN,
        ),
        TransitionRule(
            from_status=ApplicationStatus.UNDER_REVIEW,
            event="WITHDRAW",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.WITHDRAWN,
        ),
        TransitionRule(
            from_status=ApplicationStatus.NEEDS_REVISION,
            event="WITHDRAW",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.WITHDRAWN,
        ),
        TransitionRule(
            from_status=ApplicationStatus.APPROVED,
            event="WITHDRAW",
            allowed_roles=("applicant", "student", "faculty", "staff"),
            to_status=ApplicationStatus.WITHDRAWN,
        ),
    )

    @classmethod
    def get_next_state(cls, current_status: str, event: str, actor_roles: list[str]) -> str:
        for rule in cls.TRANSITIONS:
            if rule.from_status == current_status and rule.event == event:
                if any(role in rule.allowed_roles for role in actor_roles):
                    return rule.to_status
                raise IllegalTransitionError(
                    f"Actor with roles {actor_roles} is not permitted to trigger '{event}' "
                    f"from state '{current_status}'."
                )
        raise IllegalTransitionError(
            f"No valid transition found for event '{event}' from state '{current_status}'."
        )

    @classmethod
    def can_transition(cls, current_status: str, event: str, actor_roles: list[str]) -> bool:
        try:
            cls.get_next_state(current_status, event, actor_roles)
            return True
        except IllegalTransitionError:
            return False
