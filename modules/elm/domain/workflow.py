"""Pure state-transition rules for new ELM leave applications."""

from enum import StrEnum

from modules.elm.domain.leave_policy import LeaveCategory


class WorkflowTransitionError(ValueError):
    """Raised when an ELM workflow transition is not permitted."""


class LeaveWorkflowState(StrEnum):
    DRAFT = "draft"
    AWAITING_SUBSTITUTE_RESPONSE = "awaiting_substitute_response"
    APPLICANT_ACTION_REQUIRED = "applicant_action_required"
    AWAITING_UNIT_HEAD_REVIEW = "awaiting_unit_head_review"
    AWAITING_ESTABLISHMENT_ROUTING = "awaiting_establishment_routing"
    AWAITING_FINAL_SANCTION_DECISION = "awaiting_final_sanction_decision"
    AWAITING_DIRECTOR_SELF_SANCTION = "awaiting_director_self_sanction"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    CANCELLED = "cancelled"


class LeaveWorkflowAction(StrEnum):
    SUBMIT = "submit"
    ACCEPT_SUBSTITUTE = "accept_substitute"
    DECLINE_SUBSTITUTE = "decline_substitute"
    NOMINATE_REPLACEMENT = "nominate_replacement"
    WITHDRAW = "withdraw"
    UNIT_HEAD_APPROVE = "unit_head_approve"
    UNIT_HEAD_REJECT = "unit_head_reject"
    UNIT_HEAD_RECOMMEND = "unit_head_recommend"
    UNIT_HEAD_NOT_RECOMMEND = "unit_head_not_recommend"
    ROUTE_TO_FINAL_SANCTION = "route_to_final_sanction"
    FINAL_APPROVE = "final_approve"
    FINAL_REJECT = "final_reject"
    DIRECTOR_APPROVE = "director_approve"
    DIRECTOR_REJECT = "director_reject"


# Every one of these states is pending before a final decision.
# Withdrawal terminates processing from any of these states.
PENDING_STATES = frozenset(
    {
        LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE,
        LeaveWorkflowState.APPLICANT_ACTION_REQUIRED,
        LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW,
        LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING,
        LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION,
        LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION,
    }
)

HIGHER_SANCTION_CATEGORIES = frozenset(
    {
        LeaveCategory.SCL,
        LeaveCategory.EL,
        LeaveCategory.COL,
        LeaveCategory.VL,
    }
)

UNIT_HEAD_FINAL_CATEGORIES = frozenset(
    {
        LeaveCategory.CL,
        LeaveCategory.RH,
    }
)


def transition(
    current_state: LeaveWorkflowState | str,
    action: LeaveWorkflowAction | str,
    *,
    category: LeaveCategory | str,
    substitute_required: bool = False,
    applicant_is_director: bool = False,
    establishment_configured: bool = False,
) -> LeaveWorkflowState:
    """Return the next state or raise if the requested action is not legal.

    This function has no database or authorization side effects. Callers must
    authorize the actor and persist the resulting transition separately.
    """
    try:
        state = LeaveWorkflowState(current_state)
    except ValueError as err:
        raise WorkflowTransitionError(f"Unknown current workflow state: {current_state!r}") from err

    try:
        chosen_action = LeaveWorkflowAction(action)
    except ValueError as err:
        raise WorkflowTransitionError(f"Unknown workflow action: {action!r}") from err

    try:
        chosen_category = LeaveCategory(category)
    except ValueError as err:
        raise WorkflowTransitionError(f"Unknown leave category: {category!r}") from err

    if state in PENDING_STATES and chosen_action == LeaveWorkflowAction.WITHDRAW:
        return LeaveWorkflowState.WITHDRAWN

    if state == LeaveWorkflowState.DRAFT:
        if chosen_action != LeaveWorkflowAction.SUBMIT:
            raise WorkflowTransitionError("A draft can only be submitted.")

        if substitute_required:
            return LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE

        if applicant_is_director:
            return LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION

        return LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW

    if state == LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE:
        if chosen_action == LeaveWorkflowAction.ACCEPT_SUBSTITUTE:
            if applicant_is_director:
                return LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION

            return LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW

        if chosen_action == LeaveWorkflowAction.DECLINE_SUBSTITUTE:
            return LeaveWorkflowState.APPLICANT_ACTION_REQUIRED

    if (
        state == LeaveWorkflowState.APPLICANT_ACTION_REQUIRED
        and chosen_action == LeaveWorkflowAction.NOMINATE_REPLACEMENT
    ):
        return LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE

    if state == LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW:
        if chosen_category in UNIT_HEAD_FINAL_CATEGORIES:
            if chosen_action == LeaveWorkflowAction.UNIT_HEAD_APPROVE:
                return LeaveWorkflowState.APPROVED

            if chosen_action == LeaveWorkflowAction.UNIT_HEAD_REJECT:
                return LeaveWorkflowState.REJECTED

        if chosen_category in HIGHER_SANCTION_CATEGORIES and chosen_action in {
            LeaveWorkflowAction.UNIT_HEAD_RECOMMEND,
            LeaveWorkflowAction.UNIT_HEAD_NOT_RECOMMEND,
        }:
            if establishment_configured:
                return LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
            return LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION

    if (
        state == LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
        and chosen_action == LeaveWorkflowAction.ROUTE_TO_FINAL_SANCTION
    ):
        return LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION

    if state == LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION:
        if chosen_action == LeaveWorkflowAction.FINAL_APPROVE:
            return LeaveWorkflowState.APPROVED

        if chosen_action == LeaveWorkflowAction.FINAL_REJECT:
            return LeaveWorkflowState.REJECTED

    if state == LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION:
        if chosen_action == LeaveWorkflowAction.DIRECTOR_APPROVE:
            return LeaveWorkflowState.APPROVED

        if chosen_action == LeaveWorkflowAction.DIRECTOR_REJECT:
            return LeaveWorkflowState.REJECTED

    raise WorkflowTransitionError(
        f"Action {chosen_action.value!r} is not permitted from "
        f"{state.value!r} for category {chosen_category.value!r}."
    )
