"""ELM State Machine enforcing Workflows WF-EL-01 through WF-EL-05."""

from core.api.exceptions import ConflictError
from modules.elm.models import LeaveStatus


class WorkflowTransitionError(ConflictError):
    pass


def can_transition(current_status: str, target_status: str) -> bool:
    allowed_transitions = {
        LeaveStatus.DRAFT: [
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.PENDING_UNIT_HEAD,
            LeaveStatus.WITHDRAWN,
        ],
        LeaveStatus.PENDING_SUBSTITUTE: [
            LeaveStatus.PENDING_UNIT_HEAD,
            LeaveStatus.APPLICANT_ACTION_REQUIRED,
            LeaveStatus.WITHDRAWN,
        ],
        LeaveStatus.APPLICANT_ACTION_REQUIRED: [
            LeaveStatus.PENDING_SUBSTITUTE,
            LeaveStatus.WITHDRAWN,
        ],
        LeaveStatus.PENDING_UNIT_HEAD: [
            LeaveStatus.PENDING_AUTHORITY,
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
            LeaveStatus.WITHDRAWN,
        ],
        LeaveStatus.PENDING_AUTHORITY: [
            LeaveStatus.APPROVED,
            LeaveStatus.REJECTED,
            LeaveStatus.WITHDRAWN,
        ],
        LeaveStatus.APPROVED: [LeaveStatus.CANCELLED],
        LeaveStatus.REJECTED: [],
        LeaveStatus.WITHDRAWN: [],
        LeaveStatus.CANCELLED: [],
    }
    return target_status in allowed_transitions.get(current_status, [])


def determine_initial_status(has_substitute: bool) -> str:
    """WF-EL-01 Step: if substitute designated, route to substitute first."""
    if has_substitute:
        return LeaveStatus.PENDING_SUBSTITUTE
    return LeaveStatus.PENDING_UNIT_HEAD


def transition(request, target_status: str) -> None:
    """Apply a declared workflow edge or raise a 409 domain conflict."""
    if not can_transition(request.status, target_status):
        raise WorkflowTransitionError(
            f"Request cannot move from {request.status} to {target_status}."
        )
    request.status = target_status
