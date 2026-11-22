"""Finance review: queries, validation, TA verification and the budget check (UC-103, UC-402)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import ConflictError, DomainError
from modules.iaa.domain import budget, roles
from modules.iaa.domain import policy as policy_rules
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import ApprovalStep, ClarificationQuery, FinancialRecord
from modules.iaa.selectors import policy as policy_selectors
from modules.iaa.selectors import scoping
from modules.iaa.services import anomalies, notify, trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import current_policy, domain_errors, lock, now

P_REVIEW = "iaa.request.review"
VERIFY = "verify"
REJECT = "reject"


def _actor_kind(actor) -> str:
    return roles.actor_kind(role_of(actor))


@transaction.atomic
def raise_query(actor, pk: int, *, question: str) -> FinancialRecord:
    require(actor, P_REVIEW)
    if not question.strip():
        raise DomainError("Write the question the creator must answer.",
                          code="question_required")
    record = lock(scoping.records_for(actor), pk)
    with domain_errors():
        t = sm.resolve_record(record.kind, record.status, sm.RAISE_QUERY, _actor_kind(actor))
    ClarificationQuery.objects.create(record=record, question=question, raised_by=actor.user_id,
                                      raised_role=role_of(actor))
    record.status = t.to
    record.save(update_fields=["status", "updated_at"])
    trail.log("record", record.pk, "raise_query", actor=actor, frm=t.frm, to=t.to,
              remarks=question)
    notify.to_user(record.user_id, "query_raised",
                   f"Finance asked a question on #{record.pk}: answer it to continue.",
                   "record", record.pk)
    return record


def _check_budget(record: FinancialRecord, policy: policy_rules.Policy) -> None:
    if not policy.budget_check_required or record.financial_year is None:
        return
    available = policy_selectors.available_budget(record.financial_year, record.department)
    short = budget.shortfall(record.amount, available)
    if short > 0:
        # Insufficiency is flagged for review, never an automatic rejection (BR-102).
        anomalies.raise_automatic(
            record, "budget",
            f"{record.department} has {available} available in {record.financial_year}; "
            f"#{record.pk} needs {record.amount} (short by {short}).", policy)


def _route(record: FinancialRecord, policy: policy_rules.Policy) -> policy_rules.Route:
    try:
        return policy_rules.select_route(policy, record.kind, record.request_type,
                                         record.department, record.amount)
    except policy_rules.NoRoute as exc:
        raise ConflictError(
            f"No approval route is configured for a {record.kind} of {record.amount} from "
            f"{record.department}. Ask the IAA System Admin to add one.",
            code="route_missing") from exc


def _hand_to_authority(record: FinancialRecord, route: policy_rules.Route) -> None:
    record.route_levels = list(route.levels)
    record.escalation_designation = route.escalation_designation
    record.current_level = 0
    ApprovalStep.objects.create(record=record, level=0, designation=route.levels[0],
                                assigned_at=now())
    notify.to_role(route.levels[0], "approval_needed",
                   f"#{record.pk} for {record.amount} is waiting for your approval.",
                   "record", record.pk)


@transaction.atomic
def validate(actor, pk: int, *, decision: str = VERIFY, remarks: str = "") -> FinancialRecord:
    require(actor, P_REVIEW)
    record = lock(scoping.records_for(actor), pk)
    policy = current_policy()
    kind = _actor_kind(actor)
    if decision == REJECT:
        if not remarks.strip():
            raise DomainError("Give the policy reason for rejecting this claim.",
                              code="remarks_required")
        with domain_errors():
            t = sm.resolve_record(record.kind, record.status, sm.REJECT_POLICY, kind)
        record.status = t.to
        record.save(update_fields=["status", "updated_at"])
        trail.log("record", record.pk, "reject_policy", actor=actor, frm=t.frm, to=t.to,
                  remarks=remarks)
        notify.to_user(record.user_id, "rejected",
                       f"TA claim #{record.pk} was rejected by Finance: {remarks}",
                       "record", record.pk)
        return record
    if decision != VERIFY:
        raise DomainError("Decision must be 'verify' or 'reject'.", code="invalid_decision")

    if record.kind == sm.EXPENSE:
        event = sm.VALIDATE
    elif policy_rules.is_high_value(policy, record.amount):
        event = sm.VERIFY_FOR_APPROVAL
    else:
        event = sm.VERIFY
    with domain_errors():
        t = sm.resolve_record(record.kind, record.status, event, kind)
    route = _route(record, policy) if event in (sm.VALIDATE, sm.VERIFY_FOR_APPROVAL) else None
    _check_budget(record, policy)
    record.status = t.to
    if route is not None:
        _hand_to_authority(record, route)
    record.save()
    trail.log("record", record.pk, event, actor=actor, frm=t.frm, to=t.to, remarks=remarks)
    notify.to_user(record.user_id, t.to,
                   f"#{record.pk} passed Finance review and is now {t.to.replace('_', ' ')}.",
                   "record", record.pk)
    if t.to == sm.VERIFIED:
        notify.to_role(roles.FINANCE, "ready_to_record",
                       f"TA claim #{record.pk} is verified and ready to be recorded.",
                       "record", record.pk)
    return record
