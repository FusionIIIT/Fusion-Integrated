"""Review and routing service for Unit Head and Establishment.

Implements EL-UC-003, EL-UC-004, BR-EL-016, BR-EL-017, BR-EL-018, BR-EL-019.
"""

from django.db import transaction

from core.api.exceptions import BadRequestError
from fusion_auth.principal import Principal
from modules.leave.domain.constants import (
    Event,
    LeaveCategory,
    RequestStatus,
    UnitHeadRecommendation,
)
from modules.leave.models.requests import LeaveRequest
from modules.leave.models.sla import SlaTaskClock
from modules.leave.selectors.policy import get_current_policy
from modules.leave.selectors.requests import get_request_by_id
from modules.leave.services.transitions import execute_transition


def review_unit_head(
    request_id: int,
    action: str,  # "approve", "reject", "recommend", "not_recommend"
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Unit Head review: approves CL/RH; recommends higher categories."""
    req = get_request_by_id(request_id, principal)
    policy = get_current_policy()

    with transaction.atomic():
        # Stop active Unit Head SLA clock
        SlaTaskClock.objects.filter(
            request=req,
            task_type="unit_head_review",
            is_pending=True,
        ).update(is_pending=False)

        # For CL / RH: Unit Head has final authority (BR-EL-016)
        if req.category in (LeaveCategory.CL, LeaveCategory.RH):
            if action not in ("approve", "reject"):
                raise BadRequestError(
                    "Unit Head must approve or reject Casual Leave / Restricted Holiday."
                )
            event = Event.APPROVE if action == "approve" else Event.REJECT
            return execute_transition(
                request_id=req.id,
                event=event,
                actor_user_id=principal.user_id,
                actor_role="unit_head",
                remarks=remarks or f"Unit Head final decision: {action}",
            )

        # For Higher-sanction categories (SCL, EL, COL, VL): Record recommendation (BR-EL-017)
        if action not in ("recommend", "not_recommend"):
            raise BadRequestError(
                "Higher-sanction leave requires recommendation (recommend or not_recommend)."
            )

        event = Event.RECOMMEND if action == "recommend" else Event.NOT_RECOMMEND
        req.unit_head_recommendation = (
            UnitHeadRecommendation.RECOMMENDED.value
            if action == "recommend"
            else UnitHeadRecommendation.NOT_RECOMMENDED.value
        )
        req.save(update_fields=["unit_head_recommendation", "updated_at"])

        context = {
            "establishment_enabled": policy.establishment_step_enabled,
        }

        req = execute_transition(
            request_id=req.id,
            event=event,
            actor_user_id=principal.user_id,
            actor_role="unit_head",
            remarks=remarks or f"Unit Head recommendation: {action}",
            context=context,
        )

        # Start next SLA clock
        if req.status == RequestStatus.AWAITING_ESTABLISHMENT_ROUTING:
            SlaTaskClock.objects.create(
                request=req,
                task_type="establishment_routing",
                assigned_to_role="Establishment",
                state=req.status,
            )
        elif req.status == RequestStatus.AWAITING_FINAL_SANCTION_DECISION:
            SlaTaskClock.objects.create(
                request=req,
                task_type="sanction_decision",
                assigned_to_role="Sanctioning Authority",
                state=req.status,
            )

        return req


def route_establishment(
    request_id: int,
    principal: Principal,
    remarks: str = "",
) -> LeaveRequest:
    """Establishment verifies and routes higher-sanction request to Sanctioning Authority (EL-UC-004)."""
    req = get_request_by_id(request_id, principal)

    with transaction.atomic():
        # Stop establishment SLA clock
        SlaTaskClock.objects.filter(
            request=req,
            task_type="establishment_routing",
            is_pending=True,
        ).update(is_pending=False)

        req = execute_transition(
            request_id=req.id,
            event=Event.ROUTE,
            actor_user_id=principal.user_id,
            actor_role="establishment",
            remarks=remarks or "Verified and routed by Establishment",
        )

        # Start sanction SLA clock
        SlaTaskClock.objects.create(
            request=req,
            task_type="sanction_decision",
            assigned_to_role="Sanctioning Authority",
            state=req.status,
        )

        return req
