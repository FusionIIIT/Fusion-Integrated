"""Leave request state machine — pure Python, no Django imports."""
from dataclasses import dataclass
from enum import StrEnum
from typing import Optional

from .entities import LeaveCategory, LeaveStatus


class LeaveTransition(StrEnum):
    SUBMIT = "submit"
    NOMINATE_SUBSTITUTE = "nominate_substitute"
    SUBSTITUTE_ACCEPTED = "substitute_accepted"
    SUBSTITUTE_DECLINED = "substitute_declined"
    UNIT_HEAD_RECOMMEND = "unit_head_recommend"
    UNIT_HEAD_NOT_RECOMMEND = "unit_head_not_recommend"
    ESTABLISHMENT_PROCESS = "establishment_process"
    FINAL_APPROVE = "final_approve"
    FINAL_REJECT = "final_reject"
    MODIFY = "modify"
    WITHDRAW = "withdraw"
    CANCEL = "cancel"
    EXTEND = "extend"
    RESUME = "resume"
    VERIFY_RESUMPTION = "verify_resumption"
    AUTO_EXPIRE = "auto_expire"


@dataclass(frozen=True)
class Transition:
    from_status: LeaveStatus
    to_status: LeaveStatus
    transition: LeaveTransition
    required_permission: str
    allowed_categories: tuple[LeaveCategory, ...]
    requires_substitute: bool = False


# Terminal states - no outgoing transitions
TERMINAL_STATES = {
    LeaveStatus.APPROVED,
    LeaveStatus.REJECTED,
    LeaveStatus.WITHDRAWN,
    LeaveStatus.CANCELLED,
    LeaveStatus.RESUMED,
}

# All valid transitions
TRANSITIONS: tuple[Transition, ...] = (
    # Initial submission
    Transition(
        from_status=LeaveStatus.DRAFT,
        to_status=LeaveStatus.SUBMITTED,
        transition=LeaveTransition.SUBMIT,
        required_permission="leave_management.leave_request.create",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Substitute nomination (for categories requiring substitute)
    Transition(
        from_status=LeaveStatus.SUBMITTED,
        to_status=LeaveStatus.SUBSTITUTE_PENDING,
        transition=LeaveTransition.NOMINATE_SUBSTITUTE,
        required_permission="leave_management.substitute_request.create",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
        requires_substitute=True,
    ),
    # Substitute accepts
    Transition(
        from_status=LeaveStatus.SUBSTITUTE_PENDING,
        to_status=LeaveStatus.UNIT_HEAD_REVIEW,
        transition=LeaveTransition.SUBSTITUTE_ACCEPTED,
        required_permission="leave_management.substitute_request.respond",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Substitute declines - back to submitted for new nomination
    Transition(
        from_status=LeaveStatus.SUBSTITUTE_PENDING,
        to_status=LeaveStatus.SUBMITTED,
        transition=LeaveTransition.SUBSTITUTE_DECLINED,
        required_permission="leave_management.substitute_request.respond",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Unit Head review - recommend
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.ESTABLISHMENT_REVIEW,
        transition=LeaveTransition.UNIT_HEAD_RECOMMEND,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Unit Head review - not recommend (goes to final authority)
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.FINAL_SANCTION,
        transition=LeaveTransition.UNIT_HEAD_NOT_RECOMMEND,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # For CL/RH - Unit Head can directly approve/reject
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.APPROVED,
        transition=LeaveTransition.FINAL_APPROVE,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH),
    ),
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.REJECTED,
        transition=LeaveTransition.FINAL_REJECT,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH),
    ),
    # Establishment processing
    Transition(
        from_status=LeaveStatus.ESTABLISHMENT_REVIEW,
        to_status=LeaveStatus.FINAL_SANCTION,
        transition=LeaveTransition.ESTABLISHMENT_PROCESS,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Final sanctioning
    Transition(
        from_status=LeaveStatus.FINAL_SANCTION,
        to_status=LeaveStatus.APPROVED,
        transition=LeaveTransition.FINAL_APPROVE,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.FINAL_SANCTION,
        to_status=LeaveStatus.REJECTED,
        transition=LeaveTransition.FINAL_REJECT,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Modify pending request
    Transition(
        from_status=LeaveStatus.SUBMITTED,
        to_status=LeaveStatus.DRAFT,
        transition=LeaveTransition.MODIFY,
        required_permission="leave_management.leave_request.modify_pending",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.SUBSTITUTE_PENDING,
        to_status=LeaveStatus.DRAFT,
        transition=LeaveTransition.MODIFY,
        required_permission="leave_management.leave_request.modify_pending",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.DRAFT,
        transition=LeaveTransition.MODIFY,
        required_permission="leave_management.leave_request.modify_pending",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Withdraw pending request
    Transition(
        from_status=LeaveStatus.SUBMITTED,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.WITHDRAW,
        required_permission="leave_management.leave_request.withdraw_pending",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.SUBSTITUTE_PENDING,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.WITHDRAW,
        required_permission="leave_management.leave_request.withdraw_pending",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.UNIT_HEAD_REVIEW,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.WITHDRAW,
        required_permission="leave_management.leave_request.withdraw_pending",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.ESTABLISHMENT_REVIEW,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.WITHDRAW,
        required_permission="leave_management.leave_request.withdraw_pending",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.FINAL_SANCTION,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.WITHDRAW,
        required_permission="leave_management.leave_request.withdraw_pending",
        allowed_categories=(LeaveCategory.SCL, LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Cancel approved leave
    Transition(
        from_status=LeaveStatus.APPROVED,
        to_status=LeaveStatus.CANCELLED,
        transition=LeaveTransition.CANCEL,
        required_permission="leave_management.leave_request.cancel_approved",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Extend ongoing leave
    Transition(
        from_status=LeaveStatus.APPROVED,
        to_status=LeaveStatus.EXTENSION_REQUESTED,
        transition=LeaveTransition.EXTEND,
        required_permission="leave_management.leave_request.extend",
        allowed_categories=(LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Resumption of duty
    Transition(
        from_status=LeaveStatus.APPROVED,
        to_status=LeaveStatus.RESUMPTION_PENDING,
        transition=LeaveTransition.RESUME,
        required_permission="leave_management.leave_request.resume",
        allowed_categories=(LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    Transition(
        from_status=LeaveStatus.RESUMPTION_PENDING,
        to_status=LeaveStatus.RESUMED,
        transition=LeaveTransition.VERIFY_RESUMPTION,
        required_permission="leave_management.leave_request.approve",
        allowed_categories=(LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
    # Auto-expire (system)
    Transition(
        from_status=LeaveStatus.DRAFT,
        to_status=LeaveStatus.WITHDRAWN,
        transition=LeaveTransition.AUTO_EXPIRE,
        required_permission="leave_management.leave_request.auto_expire",
        allowed_categories=(LeaveCategory.CL, LeaveCategory.RH, LeaveCategory.SCL,
                           LeaveCategory.EL, LeaveCategory.VL, LeaveCategory.COL),
    ),
)


def validate_transition(
    current_status: LeaveStatus,
    target_status: LeaveStatus,
    category: LeaveCategory,
    user_permissions: set[str],
    is_substitute_action: bool = False,
) -> tuple[bool, Optional[str]]:
    """Validate if a transition is allowed.

    Returns (is_valid, error_message).
    """
    if current_status in TERMINAL_STATES:
        return False, f"Cannot transition from terminal state: {current_status.value}"

    for t in TRANSITIONS:
        if (t.from_status == current_status and
                t.to_status == target_status and
                category in t.allowed_categories):

            # Check permission
            if t.required_permission not in user_permissions and not is_substitute_action:
                return False, f"Missing required permission: {t.required_permission}"

            # Check substitute requirement
            if t.requires_substitute and not is_substitute_action:
                return False, "Substitute nomination required for this category"

            return True, None

    return False, f"Invalid transition from {current_status.value} to {target_status.value} for {category.value}"