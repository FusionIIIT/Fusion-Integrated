"""Finite State Machines for Leave, Appraisal, LTC, and CPDA."""
from modules.hr_eis.contracts import LeaveStatus, AppraisalStatus, ClaimStatus, AuthorityRoles

class InvalidStateTransitionError(Exception):
    pass

class LeaveStateMachine:
    VALID_TRANSITIONS = {
        LeaveStatus.SUBMITTED: [LeaveStatus.RECOMMENDED, LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED],
        LeaveStatus.RECOMMENDED: [LeaveStatus.APPROVED, LeaveStatus.REJECTED, LeaveStatus.CANCELLED],
        LeaveStatus.APPROVED: [LeaveStatus.CANCELLED],
        LeaveStatus.REJECTED: [],
        LeaveStatus.CANCELLED: [],
    }

    @classmethod
    def can_transition(cls, from_state, to_state, actor_role):
        if to_state not in cls.VALID_TRANSITIONS.get(from_state, []):
            return False
        if to_state == LeaveStatus.CANCELLED:
            return True
        if to_state == LeaveStatus.RECOMMENDED and actor_role not in [AuthorityRoles.HOD, AuthorityRoles.HR_ADMIN]:
            return False
        if to_state == LeaveStatus.APPROVED and actor_role not in [AuthorityRoles.DIRECTOR, AuthorityRoles.REGISTRAR, AuthorityRoles.HOD, AuthorityRoles.HR_ADMIN]:
            return False
        return True

    @classmethod
    def transition(cls, from_state, to_state, actor_role):
        if not cls.can_transition(from_state, to_state, actor_role):
            raise InvalidStateTransitionError(f"Cannot transition Leave from {from_state} to {to_state} by role '{actor_role}'.")
        return to_state

class AppraisalStateMachine:
    VALID_TRANSITIONS = {
        AppraisalStatus.DRAFT: [AppraisalStatus.SUBMITTED],
        AppraisalStatus.SUBMITTED: [AppraisalStatus.UNDER_REVIEW],
        AppraisalStatus.UNDER_REVIEW: [AppraisalStatus.FINALIZED],
        AppraisalStatus.FINALIZED: [AppraisalStatus.ARCHIVED],
        AppraisalStatus.ARCHIVED: [],
    }

    @classmethod
    def transition(cls, from_state, to_state, actor_role):
        if to_state not in cls.VALID_TRANSITIONS.get(from_state, []):
            raise InvalidStateTransitionError(f"Cannot transition Appraisal from {from_state} to {to_state}.")
        if from_state == AppraisalStatus.ARCHIVED:
            raise InvalidStateTransitionError("Archived appraisal is completely immutable.")
        return to_state

class ClaimStateMachine:
    VALID_TRANSITIONS = {
        ClaimStatus.SUBMITTED: [ClaimStatus.VERIFIED_HR, ClaimStatus.REJECTED],
        ClaimStatus.VERIFIED_HR: [ClaimStatus.APPROVED_AUTHORITY, ClaimStatus.REJECTED],
        ClaimStatus.APPROVED_AUTHORITY: [ClaimStatus.SETTLED_FINANCE, ClaimStatus.REJECTED],
        ClaimStatus.SETTLED_FINANCE: [],
        ClaimStatus.REJECTED: [],
    }

    @classmethod
    def transition(cls, from_state, to_state, actor_role):
        if to_state not in cls.VALID_TRANSITIONS.get(from_state, []):
            raise InvalidStateTransitionError(f"Cannot transition Claim from {from_state} to {to_state} by role '{actor_role}'.")
        if to_state == ClaimStatus.VERIFIED_HR and actor_role != AuthorityRoles.HR_ADMIN:
            raise InvalidStateTransitionError("Only HR Administrator can verify claim documentation.")
        if to_state == ClaimStatus.SETTLED_FINANCE and actor_role != AuthorityRoles.ACCOUNTANT:
            raise InvalidStateTransitionError("Only Accountant can settle approved claims.")
        return to_state
