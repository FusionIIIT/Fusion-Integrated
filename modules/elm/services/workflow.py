"""Pure state-transition rules for new ELM leave applications."""

from enum import StrEnum

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain.leave_policy import LeaveCategory
from modules.elm.models import LeaveApplication, LeaveApplicationTransition
from modules.elm.services.authz import require


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


@transaction.atomic
def transition(
    application_id: int,
    action: LeaveWorkflowAction,
    *,
    category: LeaveCategory,
    substitute_required: bool = False,
    applicant_is_director: bool = False,
    establishment_configured: bool = False,
    actor,
) -> LeaveApplication:
    """Return the next state or raise if the requested action is not legal.

    The caller supplies the actor and workflow context; this boundary enforces
    permission grants and persists the transition atomically.
    """
    application = LeaveApplication.objects.select_for_update().get(pk=application_id)

    try:
        state = LeaveWorkflowState(application.status)
    except ValueError as err:
        raise WorkflowTransitionError(
            f"Unknown current workflow state: {application.status!r}"
        ) from err

    try:
        chosen_action = LeaveWorkflowAction(action)
    except ValueError as err:
        raise WorkflowTransitionError(f"Unknown workflow action: {action!r}") from err

    try:
        chosen_category = LeaveCategory(category)
    except ValueError as err:
        raise WorkflowTransitionError(f"Unknown leave category: {category!r}") from err
    if chosen_category.value != application.category:
        raise WorkflowTransitionError("The supplied category does not match the application.")

    if state in PENDING_STATES and chosen_action == LeaveWorkflowAction.WITHDRAW:
        require(actor, "elm.leave_application.withdraw")
        if application.user_id != actor.user_id:
            raise PermissionDeniedError("Only the applicant can withdraw the application.")
        application.status = LeaveWorkflowState.WITHDRAWN
        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState(state),
            to_status=LeaveWorkflowState.WITHDRAWN,
            action=LeaveWorkflowAction.WITHDRAW,
            actor_user_id=actor.user_id,
        )
        return application

    if state == LeaveWorkflowState.DRAFT:
        if chosen_action != LeaveWorkflowAction.SUBMIT:
            raise WorkflowTransitionError("Only submit is permitted from draft.")
        require(actor, "elm.leave_application.submit")
        if application.user_id != actor.user_id:
            raise PermissionDeniedError("Only the applicant can submit the application.")

        if substitute_required:
            application.status = LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE
        elif applicant_is_director:
            application.status = LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION
        else:
            application.status = LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW

        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.DRAFT,
            to_status=application.status,
            action=LeaveWorkflowAction.SUBMIT,
            actor_user_id=actor.user_id,
        )
        return application

    if state == LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE:
        if chosen_action not in {
            LeaveWorkflowAction.ACCEPT_SUBSTITUTE,
            LeaveWorkflowAction.DECLINE_SUBSTITUTE,
        }:
            raise WorkflowTransitionError("Only a substitute response is permitted in this state.")
        require(actor, "elm.substitute_consent.respond")
        if application.user_id == actor.user_id:
            raise PermissionDeniedError("The applicant cannot respond as their own substitute.")

        substitute_consent = application.substitute_consents.filter(
            substitute_user_id=actor.user_id, response_status="pending"
        ).first()
        if not substitute_consent:
            raise PermissionDeniedError(
                "Only the nominated substitute can respond to this request."
            )

        if chosen_action == LeaveWorkflowAction.ACCEPT_SUBSTITUTE:
            substitute_consent.response_status = "accepted"
            substitute_consent.responded_at = timezone.now()
            substitute_consent.save()
            if applicant_is_director:
                application.status = LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION
            else:
                application.status = LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW

        if chosen_action == LeaveWorkflowAction.DECLINE_SUBSTITUTE:
            substitute_consent.response_status = "declined"
            substitute_consent.responded_at = timezone.now()
            substitute_consent.save()
            application.status = LeaveWorkflowState.APPLICANT_ACTION_REQUIRED

        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE,
            to_status=application.status,
            action=chosen_action,
            actor_user_id=actor.user_id,
        )
        return application

    if (
        state == LeaveWorkflowState.APPLICANT_ACTION_REQUIRED
        and chosen_action == LeaveWorkflowAction.NOMINATE_REPLACEMENT
    ):
        require(actor, "elm.leave_application.submit")
        if application.user_id != actor.user_id:
            raise PermissionDeniedError("Only the applicant can nominate a replacement.")

        application.status = LeaveWorkflowState.AWAITING_SUBSTITUTE_RESPONSE
        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.APPLICANT_ACTION_REQUIRED,
            to_status=application.status,
            action=LeaveWorkflowAction.NOMINATE_REPLACEMENT,
            actor_user_id=actor.user_id,
        )
        return application

    if state == LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW:
        require(actor, "elm.leave_application.review")
        if chosen_category in UNIT_HEAD_FINAL_CATEGORIES:
            if chosen_action == LeaveWorkflowAction.UNIT_HEAD_APPROVE:
                application.status = LeaveWorkflowState.APPROVED
            elif chosen_action == LeaveWorkflowAction.UNIT_HEAD_REJECT:
                application.status = LeaveWorkflowState.REJECTED
            else:
                raise WorkflowTransitionError("Unit head must approve or reject this category.")

        elif chosen_category in HIGHER_SANCTION_CATEGORIES and chosen_action in {
            LeaveWorkflowAction.UNIT_HEAD_RECOMMEND,
            LeaveWorkflowAction.UNIT_HEAD_NOT_RECOMMEND,
        }:
            if establishment_configured:
                application.status = LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
            else:
                application.status = LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION
        else:
            raise WorkflowTransitionError("This action is not permitted for the category.")

        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.AWAITING_UNIT_HEAD_REVIEW,
            to_status=application.status,
            action=chosen_action,
            actor_user_id=actor.user_id,
        )
        return application

    if (
        state == LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING
        and chosen_action == LeaveWorkflowAction.ROUTE_TO_FINAL_SANCTION
    ):
        require(actor, "elm.leave_application.route")
        application.status = LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION
        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.AWAITING_ESTABLISHMENT_ROUTING,
            to_status=application.status,
            action=LeaveWorkflowAction.ROUTE_TO_FINAL_SANCTION,
            actor_user_id=actor.user_id,
        )
        return application

    if state == LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION:
        require(actor, "elm.leave_application.finalize")
        if chosen_action == LeaveWorkflowAction.FINAL_APPROVE:
            application.status = LeaveWorkflowState.APPROVED
        elif chosen_action == LeaveWorkflowAction.FINAL_REJECT:
            application.status = LeaveWorkflowState.REJECTED
        else:
            raise WorkflowTransitionError("Final authority must approve or reject.")

        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.AWAITING_FINAL_SANCTION_DECISION,
            to_status=application.status,
            action=chosen_action,
            actor_user_id=actor.user_id,
        )
        return application

    if state == LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION:
        require(actor, "elm.leave_application.self_sanction")
        if chosen_action == LeaveWorkflowAction.DIRECTOR_APPROVE:
            application.status = LeaveWorkflowState.APPROVED
        elif chosen_action == LeaveWorkflowAction.DIRECTOR_REJECT:
            application.status = LeaveWorkflowState.REJECTED
        else:
            raise WorkflowTransitionError("Director must approve or reject.")

        application.save()
        LeaveApplicationTransition.objects.create(
            application=application,
            from_status=LeaveWorkflowState.AWAITING_DIRECTOR_SELF_SANCTION,
            to_status=application.status,
            action=chosen_action,
            actor_user_id=actor.user_id,
        )
        return application

    raise WorkflowTransitionError(
        f"Action {chosen_action.value!r} is not permitted from "
        f"{state.value!r} for category {chosen_category.value!r}."
    )
