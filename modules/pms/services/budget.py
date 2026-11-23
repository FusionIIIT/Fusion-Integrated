"""Budgets: proposal, Director decision, escalation (UC-PMS-009, 027; BR-PMS-048..053)."""
from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.pms.domain import budget as bd
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Budget, FinancialRecord
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import escalations, notifications
from modules.pms.services.base import (
    accepted_attorney_only,
    lock,
    lock_application,
    move_record,
    now,
    require,
    ruled,
    today,
)

P_PROPOSE = "pms.budget.create"
P_DECIDE = "pms.budget.approve"
P_ESCALATION = "pms.escalation.review"


def _record(app, budget, kind: str, level: str, actor, reference: str = "") -> None:
    FinancialRecord.objects.create(application=app, budget=budget, kind=kind,
                                   amount=budget.total, authorization_level=level,
                                   availability=budget.availability or bd.NOT_AVAILABLE,
                                   recorded_by_user_id=actor.user_id, reference=reference)


def _tell(app, budget, words: str) -> None:
    """PMS-AFR-197: the attorney and the applicant hear every budget outcome."""
    notifications.enqueue_many(
        topic="budget.decided", key=f"budget:{budget.pk}:{budget.status}",
        recipients=[budget.proposed_by_user_id, app.applicant_user_id],
        subject=f"Budget {words}: {app.reference}",
        body=f"The filing budget of Rs {budget.total} for {app.reference} was {words}.")


@ruled
def propose(*, actor, pk: int, filing_fee, attorney_fee, admin_cost) -> Budget:
    require(actor, P_PROPOSE)
    f, a, m, total = bd.check_components(filing_fee, attorney_fee, admin_cost)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        accepted_attorney_only(actor, app)
        if not bd.application_allows_budget(app.status):
            raise ConflictError("A budget can be proposed only for a Director-approved "
                                "application that is not yet filed (BR-PMS-052).",
                                code="budget_not_allowed")
        if app.budgets.filter(status__in=sorted(sm.APPROVED_BUDGET)).exists():
            raise ConflictError("This application already has an approved budget.",
                                code="budget_already_approved")
        if app.budgets.filter(status__in=sorted(sm.OPEN_BUDGET)).exists():
            raise ConflictError("A budget for this application is already awaiting a decision.",
                                code="budget_open")
        budget = Budget(application=app, proposed_by_user_id=actor.user_id, filing_fee=f,
                        attorney_fee=a, admin_cost=m, total=total)
        move_record(sm.BUDGET, budget, "propose", sm.ATTORNEY, actor, application=app,
                    details={"total": str(total)})
        latest = app.review_cycles.order_by("-cycle_no").first()
        notifications.enqueue_many(
            topic="budget.proposed", key=f"budget.proposed:{budget.pk}",
            recipients=[getattr(latest, "director_user_id", None)],
            subject=f"Budget to decide: {app.reference}",
            body=f"A filing and prosecution budget of Rs {total} is waiting for your decision.")
    return budget


def _locked_budget(actor, budget_id: int):
    budget = scoping.budgets_for(actor).filter(pk=budget_id).first()
    if budget is None:
        raise NotFoundError("No such budget.", code="not_found")
    app = lock_application(budget.application_id)
    return app, Budget.objects.select_for_update().get(pk=budget_id)


@ruled
def decide(*, actor, budget_id: int, approve: bool, note: str = "") -> Budget:
    """Above the threshold a decision becomes an escalation, never an invented approval."""
    require(actor, P_DECIDE)
    with transaction.atomic():
        app, budget = _locked_budget(actor, budget_id)
        sm.BUDGET.resolve(budget.status, "approve" if approve else "reject", sm.DIRECTOR)
        if scoping.reviewing_director_id(app) != actor.user_id:
            raise PermissionDeniedError("Only the Director who reviewed the application decides "
                                        "its budget.", code="not_assigned")
        if not bd.application_allows_budget(app.status):
            raise ConflictError("The application is no longer Director-approved and unfiled, "
                                "so its budget cannot be decided.", code="budget_not_allowed")
        spec = policy_selector.current()
        over = bd.exceeds_threshold(budget.total, spec.cost_threshold)
        event = "escalate" if over else ("approve" if approve else "reject")
        budget.decided_by_user_id, budget.decided_at = actor.user_id, now()
        budget.decision_note = (note or "").strip()[:2000]
        budget.threshold_at_decision = spec.cost_threshold
        budget.availability = bd.NOT_AVAILABLE
        move_record(sm.BUDGET, budget, event, sm.DIRECTOR, actor, application=app,
                    extra_fields=("decided_by_user_id", "decided_at", "decision_note",
                                  "threshold_at_decision", "availability"))
        kind = {"escalate": "budget_escalated", "approve": "budget_approved",
                "reject": "budget_rejected"}[event]
        _record(app, budget, kind, "director", actor)
        if over:
            escalations.raise_case("budget_threshold", app, budget.pk,
                                   note=f"Total Rs {budget.total} exceeds the threshold.")
        _tell(app, budget, {"escalate": "escalated to the higher authority",
                            "approve": "approved", "reject": "rejected"}[event])
    return budget


@ruled
def route_escalation(*, actor, budget_id: int, routed_to: str) -> Budget:
    """BW-PMS-10: PCC_ADMIN names who decides; PMS does not decide for them."""
    require(actor, P_ESCALATION)
    target = (routed_to or "").strip()
    if not target or len(target) > 200:
        raise InvalidInput("Name the authority the case was routed to.", code="target_required")
    with transaction.atomic():
        app, budget = _locked_budget(actor, budget_id)
        budget.routed_to = target
        move_record(sm.BUDGET, budget, "route", sm.PCC_ADMIN, actor, application=app,
                    extra_fields=("routed_to",))
        escalations.resolve_open(app, ("budget_threshold",), actor, f"Routed to {target}.")
    return budget


@ruled
def record_external_decision(*, actor, budget_id: int, approved: bool, reference: str,
                             decided_on: date) -> Budget:
    """Ruling C14: the outside authority's own decision, recorded with its reference."""
    require(actor, P_ESCALATION)
    ref = (reference or "").strip()
    if not ref or len(ref) > 200:
        raise InvalidInput("Give the reference of the authority's decision.",
                           code="reference_required")
    if decided_on > today():
        raise InvalidInput("The decision date cannot be in the future.", code="date_in_future")
    with transaction.atomic():
        app, budget = _locked_budget(actor, budget_id)
        event = "record_external_approval" if approved else "record_external_rejection"
        budget.external_reference, budget.external_decided_on = ref, decided_on
        move_record(sm.BUDGET, budget, event, sm.PCC_ADMIN, actor, application=app,
                    extra_fields=("external_reference", "external_decided_on"))
        _record(app, budget, "external_approved" if approved else "external_rejected",
                "external_authority", actor, reference=ref)
        _tell(app, budget, "approved by the higher authority" if approved
              else "rejected by the higher authority")
    return budget
