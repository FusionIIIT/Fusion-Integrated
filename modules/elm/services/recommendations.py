
"""Unit Head recommendations for higher-sanction leave applications."""

from django.db import transaction

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import (
    LeaveApplication,
    LeaveApplicationStatus,
    LeaveType,
)


RECOMMENDED = "recommended"
NOT_RECOMMENDED = "not_recommended"

HIGHER_SANCTION_TYPES = {
    LeaveType.SCL,
    LeaveType.EL,
    LeaveType.COL,
    LeaveType.VL,
}


@transaction.atomic
def recommend_leave_application(
    *,
    actor,
    application_id: int,
    recommendation: str,
    remarks: str = "",
) -> LeaveApplication:
    """Record the Unit Head's recommendation and forward the request."""

    application = (
        LeaveApplication.objects.select_for_update()
        .filter(pk=application_id)
        .first()
    )

    if application is None:
        raise LeaveRuleError("Leave application does not exist.")

    if actor is None:
        raise PermissionDeniedError(
            "Authentication required.",
            code="not_authenticated",
        )

    check = getattr(actor, "has_permission", None)
    if not callable(check) or not check(
        "elm.leave_application.recommend"
    ):
        raise PermissionDeniedError(
            "You do not have permission to recommend leave applications.",
            code="permission_denied",
        )

    if (
        application.assigned_unit_head_user_id is None
        or getattr(actor, "user_id", None)
        != application.assigned_unit_head_user_id
    ):
        raise PermissionDeniedError(
            "You are not the Unit Head assigned to this request.",
            code="permission_denied",
        )

    if application.status != LeaveApplicationStatus.PENDING:
        raise LeaveRuleError(
            "Only pending leave applications can be recommended."
        )

    if application.leave_type not in HIGHER_SANCTION_TYPES:
        raise LeaveRuleError(
            "Unit Head recommendations apply only to higher-sanction leave."
        )

    if application.workflow_stage != "awaiting_unit_head_review":
        raise LeaveRuleError(
            "This application is not awaiting Unit Head review."
        )

    if recommendation not in {RECOMMENDED, NOT_RECOMMENDED}:
        raise LeaveRuleError(
            "Recommendation must be recommended or not_recommended."
        )

    if application.assigned_final_authority_user_id is None:
        raise LeaveRuleError(
            "No final sanctioning authority is assigned to this request."
        )

    application.unit_head_recommendation = recommendation
    application.unit_head_recommendation_remarks = remarks.strip()
    application.unit_head_recommended_by_user_id = actor.user_id

    if application.establishment_required:
        application.workflow_stage = "awaiting_establishment"
    else:
        application.workflow_stage = "awaiting_final_sanction"

    application.save(
        update_fields=[
            "unit_head_recommendation",
            "unit_head_recommendation_remarks",
            "unit_head_recommended_by_user_id",
            "workflow_stage",
            "updated_at",
        ]
    )

    return application
