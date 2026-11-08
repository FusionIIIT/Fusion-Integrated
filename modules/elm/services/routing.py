"""Fail-closed routing resolution for Employee Leave Management."""

from dataclasses import dataclass

from core.api.exceptions import PermissionDeniedError
from modules.directory.contracts import get_users
from modules.elm.domain.leave_rules import LeaveRuleError
from modules.elm.models import LeaveRoutingRule, LeaveType


@dataclass(frozen=True)
class LeaveRoute:
    unit_head_user_id: int | None
    final_authority_user_id: int
    establishment_required: bool
    workflow_stage: str


def _require_active_employee(user_id: int, label: str) -> None:
    employee = get_users([user_id]).get(user_id)

    if employee is None or not employee.is_active:
        raise LeaveRuleError(f"The configured {label} is missing or inactive in the directory.")


def resolve_leave_route(
    *,
    actor,
    applicant_user_id: int,
    leave_type: str,
) -> LeaveRoute:
    """Resolve one unambiguous route from current configured data."""

    if actor is None or getattr(actor, "user_id", None) != applicant_user_id:
        raise PermissionDeniedError(
            "Routing can only be resolved for the authenticated applicant.",
            code="permission_denied",
        )

    designation = getattr(actor, "active_role", None)

    if not designation:
        raise LeaveRuleError("Select an active designation before submitting a leave request.")

    applicant = get_users([applicant_user_id]).get(applicant_user_id)

    if applicant is None or not applicant.is_active:
        raise LeaveRuleError("Applicant directory information is missing or inactive.")

    if not applicant.department:
        raise LeaveRuleError("Applicant department is missing. Contact the ELM administrator.")

    rules = LeaveRoutingRule.objects.filter(
        department=applicant.department,
        applicant_designation=designation,
        leave_type=leave_type,
        is_active=True,
    )

    if rules.count() != 1:
        raise LeaveRuleError(
            "No unique active routing rule exists for this applicant "
            "and leave category. Contact the ELM administrator."
        )

    rule = rules.get()

    if rule.director_self_sanction:
        return LeaveRoute(
            unit_head_user_id=None,
            final_authority_user_id=applicant_user_id,
            establishment_required=False,
            workflow_stage="awaiting_director_self_sanction",
        )

    if not rule.unit_head_user_id:
        raise LeaveRuleError("The routing rule has no configured Unit Head.")

    _require_active_employee(
        rule.unit_head_user_id,
        "Unit Head",
    )

    if leave_type in {LeaveType.CL, LeaveType.RH}:
        final_authority_id = rule.unit_head_user_id
    else:
        final_authority_id = rule.final_authority_user_id

        if not final_authority_id:
            raise LeaveRuleError("The routing rule has no configured final sanctioning authority.")

        _require_active_employee(
            final_authority_id,
            "final sanctioning authority",
        )

    if rule.establishment_required and leave_type in {
        LeaveType.CL,
        LeaveType.RH,
    }:
        raise LeaveRuleError("Establishment processing cannot be configured for CL/RH routing.")

    return LeaveRoute(
        unit_head_user_id=rule.unit_head_user_id,
        final_authority_user_id=final_authority_id,
        establishment_required=rule.establishment_required,
        workflow_stage="awaiting_unit_head_review",
    )
