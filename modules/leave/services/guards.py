"""Every guard named in the transition table, implemented once.

A guard that does not exist is a refusal, not a no-op: a typo in the table must
fail closed, or an unnamed condition silently stops being enforced.
"""
from __future__ import annotations

from datetime import date

from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.leave.domain import categories as cat
from modules.leave.domain import state_machine as sm
from modules.leave.domain.errors import RuleViolation
from modules.leave.models import SubstituteAssignment
from modules.leave.selectors import config as config_selector
from modules.leave.services import facts


def check(name: str, *, row, actor, reason: str = "", context: dict | None = None):
    """Run one guard, translating a rule refusal into an API-shaped conflict."""
    handler = _GUARDS.get(name)
    if handler is None:
        raise ConflictError(f"The guard {name!r} is not implemented.",
                            code="guard_missing")
    context = context or {}
    try:
        handler(row=row, actor=actor, reason=reason, context=context)
    except RuleViolation as exc:
        raise ConflictError(exc.message, code=exc.code, details=exc.details) from exc


def _self_sanction_role() -> str:
    return config_selector.current_policy().self_sanction_designation


def _g_request_valid(*, row, actor, reason, context) -> None:
    days = facts.evaluate(row)
    row.days_requested = days


def _g_parent_approved(*, row, actor, reason, context) -> None:
    if row.parent is None or row.parent.status != sm.APPROVED:
        raise RuleViolation(
            "Only a leave that has been approved can be cancelled.",
            code="not_approved")


def _g_parent_ongoing_extendable(*, row, actor, reason, context) -> None:
    parent = row.parent
    today = context.get("today") or timezone.localdate()
    if parent is None or parent.status != sm.APPROVED:
        raise RuleViolation("Only an approved leave can be extended.",
                            code="not_approved")
    if not cat.is_extendable(parent.category):
        raise RuleViolation(
            f"A {cat.LABELS[parent.category]} cannot be extended.",
            code="not_extendable")
    if not (parent.start_date <= today <= parent.end_date):
        raise RuleViolation(
            "An extension can be asked for only while the leave is ongoing.",
            code="not_ongoing")


def _g_substitute_required(*, row, actor, reason, context) -> None:
    if not row.substitute_required:
        raise RuleViolation("This request does not need a substitute.",
                            code="substitute_not_required")


def _g_no_substitute_required(*, row, actor, reason, context) -> None:
    if row.substitute_required:
        raise RuleViolation(
            "Nominate a substitute before submitting: responsibility coverage is "
            "required for this leave.",
            code="substitute_required")


def _g_substitute_nominated(*, row, actor, reason, context) -> None:
    if not SubstituteAssignment.objects.filter(request=row, state="pending").exists():
        raise RuleViolation(
            "Nominate exactly one eligible substitute before submitting.",
            code="substitute_required")


def _assignment(row, actor):
    return (SubstituteAssignment.objects
            .filter(request=row, substitute_user_id=getattr(actor, "user_id", None))
            .order_by("-id").first())


def _g_substitute_accepted(*, row, actor, reason, context) -> None:
    assignment = _assignment(row, actor)
    if assignment is None or assignment.state != "accepted":
        raise RuleViolation("Record your decision on the responsibility request first.",
                            code="substitute_not_responded")


def _g_substitute_declined(*, row, actor, reason, context) -> None:
    assignment = _assignment(row, actor)
    if assignment is None or assignment.state != "declined":
        raise RuleViolation("Record your decision on the responsibility request first.",
                            code="substitute_not_responded")


def _g_replacement_eligible(*, row, actor, reason, context) -> None:
    _g_substitute_nominated(row=row, actor=actor, reason=reason, context=context)


def _g_applicant_is_director(*, row, actor, reason, context) -> None:
    if (row.applicant_role or "") != _self_sanction_role():
        raise RuleViolation(
            f"Only the {_self_sanction_role()} self-sanctions their own leave.",
            code="not_self_sanction")


def _g_applicant_not_director(*, row, actor, reason, context) -> None:
    if (row.applicant_role or "") == _self_sanction_role():
        raise RuleViolation(
            "The self-sanction route applies to this applicant, not this one.",
            code="self_sanction")


def _g_unit_head_final_category(*, row, actor, reason, context) -> None:
    if not cat.unit_head_is_final(row.category):
        raise RuleViolation(
            f"The Unit Head only decides {', '.join(sorted(cat.UNIT_HEAD_FINAL))} "
            "outright; this category continues to the sanctioning authority.",
            code="not_unit_head_final")


def _g_higher_sanction(*, row, actor, reason, context) -> None:
    if not cat.requires_higher_sanction(row.category):
        raise RuleViolation(
            f"{cat.LABELS[row.category]} does not need a higher sanction.",
            code="not_higher_sanction")


def _g_establishment_configured(*, row, actor, reason, context) -> None:
    if facts.path_for(row).establishment is None:
        raise RuleViolation("No Establishment step is configured for this path.",
                            code="no_establishment_step")


def _g_no_establishment_step(*, row, actor, reason, context) -> None:
    if facts.path_for(row).establishment is not None:
        raise RuleViolation(
            "An Establishment step is configured, so the request must go through it.",
            code="establishment_required")


def _g_routing_context_valid(*, row, actor, reason, context) -> None:
    path = facts.path_for(row)
    if path.final is None:
        raise RuleViolation(
            "No final sanctioning authority is configured, so the request cannot be "
            "forwarded.",
            code="routing_not_configured")


def _g_has_reason(*, row, actor, reason, context) -> None:
    if not (reason or "").strip():
        raise RuleViolation("A reason is required for this decision.",
                            code="reason_required")


def _g_not_own_request(*, row, actor, reason, context) -> None:
    if getattr(actor, "user_id", None) == row.user_id:
        raise RuleViolation("You cannot decide your own leave request.",
                            code="self_approval")


def _g_not_started(*, row, actor, reason, context) -> None:
    today = context.get("today") or timezone.localdate()
    if row.parent is not None and row.parent.start_date <= today:
        raise RuleViolation(
            "A leave that has already started cannot be cancelled; an extension or "
            "a resumption applies instead.",
            code="leave_started")


def _g_resumption_reviewed_category(*, row, actor, reason, context) -> None:
    if not cat.is_resumption_reviewed(row.category):
        raise RuleViolation(
            f"{cat.LABELS[row.category]} does not go through formal resumption review.",
            code="resumption_not_applicable")


def _actual_date(context) -> date:
    actual = context.get("actual_date")
    if not isinstance(actual, date):
        raise RuleViolation("An actual resumption date is required.",
                            code="actual_date_required")
    return actual


def _g_resumption_dates_match(*, row, actor, reason, context) -> None:
    if _actual_date(context) != row.end_date:
        raise RuleViolation(
            "The actual resumption date is not the approved end date.",
            code="resumption_outcome_mismatch")


def _g_resumption_early(*, row, actor, reason, context) -> None:
    if _actual_date(context) >= row.end_date:
        raise RuleViolation(
            "An early resumption has to fall before the approved end date.",
            code="resumption_outcome_mismatch")


def _g_resumption_late(*, row, actor, reason, context) -> None:
    if _actual_date(context) <= row.end_date:
        raise RuleViolation(
            "A late resumption has to fall after the approved end date.",
            code="resumption_outcome_mismatch")


def _g_not_finally_approved(*, row, actor, reason, context) -> None:
    if row.status == sm.APPROVED:
        raise RuleViolation(
            "This leave is already approved, so it can no longer be withdrawn.",
            code="already_approved")


def _g_original_unit_head_final(*, row, actor, reason, context) -> None:
    """BR-EL-016: the cancellation path for CL/RH ends at the Unit Head."""
    if not cat.unit_head_is_final(row.parent.category if row.parent else row.category):
        raise RuleViolation(
            "This cancellation does not end at the Unit Head; it continues to the "
            "sanctioning authority.",
            code="not_unit_head_final")


_GUARDS = {
    "request_valid": _g_request_valid,
    "parent_approved": _g_parent_approved,
    "parent_ongoing_extendable": _g_parent_ongoing_extendable,
    "substitute_required": _g_substitute_required,
    "no_substitute_required": _g_no_substitute_required,
    "substitute_nominated": _g_substitute_nominated,
    "substitute_accepted": _g_substitute_accepted,
    "substitute_declined": _g_substitute_declined,
    "replacement_eligible": _g_replacement_eligible,
    "applicant_is_director": _g_applicant_is_director,
    "applicant_not_director": _g_applicant_not_director,
    "unit_head_final_category": _g_unit_head_final_category,
    "higher_sanction": _g_higher_sanction,
    "establishment_configured": _g_establishment_configured,
    "no_establishment_step": _g_no_establishment_step,
    "routing_context_valid": _g_routing_context_valid,
    "has_reason": _g_has_reason,
    "not_own_request": _g_not_own_request,
    "not_started": _g_not_started,
    "resumption_reviewed_category": _g_resumption_reviewed_category,
    "resumption_dates_match": _g_resumption_dates_match,
    "resumption_early": _g_resumption_early,
    "resumption_late": _g_resumption_late,
    "not_finally_approved": _g_not_finally_approved,
    "original_unit_head_final": _g_original_unit_head_final,
}


def names() -> frozenset[str]:
    return frozenset(_GUARDS)
