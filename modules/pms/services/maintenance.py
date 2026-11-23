"""Post-grant maintenance (UC-PMS-017, 018; BR-PMS-059..061, 100; rulings C19, Q-12)."""
from __future__ import annotations

from datetime import date

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.pms.domain import budget as bd
from modules.pms.domain import post_grant as pg
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import FinancialRecord, MaintenanceCycle
from modules.pms.selectors import candidates, scoping
from modules.pms.selectors import policy as policy_selector
from modules.pms.services import audit, escalations, notifications
from modules.pms.services.base import (
    accepted_attorney_only,
    conflicted,
    lock,
    lock_application,
    move_record,
    now,
    require,
    ruled,
    today,
)

P_TRACK = "pms.maintenance.update"
P_DECIDE = "pms.renewal.approve"
P_REASSIGN = "pms.renewal.assign"


def _next_seq(app) -> int:
    last = app.maintenance_cycles.order_by("-seq").values_list("seq", flat=True).first()
    return (last or 0) + 1


def schedule_next(app, *, after: date) -> MaintenanceCycle | None:
    """BR-PMS-060 / PMS-AFR-115: the next due date from the rules, or nothing invented."""
    rules = policy_selector.current().maintenance_rules
    due = pg.next_due(app.grant_date, app.grant_jurisdiction, rules, after=after)
    if due is None:
        return None
    return MaintenanceCycle.objects.create(application=app, seq=_next_seq(app), due_on=due,
                                           source="schedule")


def activate(app) -> MaintenanceCycle | None:
    """BR-PMS-059: tracking starts the moment the application is Granted."""
    return schedule_next(app, after=today()) if pg.may_track(app.status) else None


def _locked_cycle(actor, cycle_id: int):
    cycle = scoping.maintenance_for(actor).filter(pk=cycle_id).first()
    if cycle is None:
        raise NotFoundError("No such maintenance cycle.", code="not_found")
    app = lock_application(cycle.application_id)
    return app, MaintenanceCycle.objects.select_for_update().get(pk=cycle_id)


@ruled
def add_cycle(*, actor, pk: int, due_on: date) -> MaintenanceCycle:
    """Blueprint Q-12: with no schedule rule, the attorney enters the office's due date."""
    require(actor, P_TRACK)
    if due_on <= today():
        raise InvalidInput("The maintenance due date must be in the future.",
                           code="date_not_future")
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        accepted_attorney_only(actor, app)
        if not pg.may_track(app.status):
            raise ConflictError("Maintenance is tracked only for granted patents.",
                                code="not_granted")
        try:
            with transaction.atomic():
                cycle = MaintenanceCycle.objects.create(application=app, seq=_next_seq(app),
                                                        due_on=due_on, source="manual")
        except IntegrityError as exc:
            raise ConflictError("A maintenance cycle is already open for this patent.",
                                code="cycle_open") from exc
        audit.record(actor, "maintenance.cycle_added", application=app, obj=cycle,
                     to=sm.SCHEDULED, details={"due_on": due_on.isoformat()})
    return cycle


@ruled
def request_decision(*, actor, cycle_id: int) -> MaintenanceCycle:
    """PMS-AFR-111: the reviewing Director decides; if they have left, PCC_ADMIN reassigns."""
    require(actor, P_TRACK)
    with transaction.atomic():
        app, cycle = _locked_cycle(actor, cycle_id)
        accepted_attorney_only(actor, app)
        sm.MAINTENANCE.resolve(cycle.status, "request", sm.ATTORNEY)
        decider = scoping.reviewing_director_id(app)
        cycle.deciding_director_user_id, cycle.requested_at = decider, now()
        move_record(sm.MAINTENANCE, cycle, "request", sm.ATTORNEY, actor, application=app,
                    extra_fields=("deciding_director_user_id", "requested_at"))
        if decider is None or not candidates.is_active_director(decider):
            escalations.raise_case("inactive_renewal_director", app, cycle.pk,
                                   deadline=cycle.due_on)
        else:
            notifications.enqueue(
                topic="renewal.requested", dedupe_key=f"renewal.requested:{cycle.pk}",
                recipient_user_id=decider, subject=f"Renewal decision due: {app.reference}",
                body=f"Decide Renew or Do Not Renew for {app.reference} by "
                     f"{cycle.due_on.isoformat()}.")
    return cycle


@ruled
def decide(*, actor, cycle_id: int, renew: bool, note: str = "") -> MaintenanceCycle:
    require(actor, P_DECIDE)
    event = "renew" if renew else "do_not_renew"
    with transaction.atomic():
        app, cycle = _locked_cycle(actor, cycle_id)
        sm.MAINTENANCE.resolve(cycle.status, event, sm.DIRECTOR)
        if cycle.deciding_director_user_id != actor.user_id:
            raise PermissionDeniedError("Only the Director asked to decide this renewal can "
                                        "decide it.", code="not_assigned")
        if not pg.decision_open(cycle.due_on, today()):
            raise ConflictError(f"The maintenance deadline was {cycle.due_on.isoformat()}; the "
                                f"missed deadline has been escalated to PCC_ADMIN.",
                                code="renewal_deadline_passed")
        cycle.decided_at, cycle.decision_note = now(), (note or "").strip()[:2000]
        move_record(sm.MAINTENANCE, cycle, event, sm.DIRECTOR, actor, application=app,
                    extra_fields=("decided_at", "decision_note"))
        attorney = app.attorney_assignments.filter(status=sm.ACCEPTED).first()
        notifications.enqueue_many(
            topic="renewal.decided", key=f"renewal.decided:{cycle.pk}",
            recipients=[getattr(attorney, "attorney_user_id", None), app.applicant_user_id],
            subject=f"Renewal decision: {app.reference}",
            body=f"The Director decided {'Renew' if renew else 'Do Not Renew'} for "
                 f"{app.reference} (due {cycle.due_on.isoformat()}).")
    return cycle


@ruled
def record_action(*, actor, cycle_id: int, reference: str, amount,
                  actioned_on: date) -> MaintenanceCycle:
    """PMS-AFR-113: the payment is made outside PMS; PMS records it and schedules the next."""
    require(actor, P_TRACK)
    ref = (reference or "").strip()
    if not ref or len(ref) > 200:
        raise InvalidInput("Give the patent office's receipt or transaction reference.",
                           code="reference_required")
    paid = bd.amount(amount, "maintenance fee")
    if actioned_on > today():
        raise InvalidInput("The payment date cannot be in the future.", code="date_in_future")
    with transaction.atomic():
        app, cycle = _locked_cycle(actor, cycle_id)
        accepted_attorney_only(actor, app)
        sm.MAINTENANCE.resolve(cycle.status, "record_action", sm.ATTORNEY)
        cycle.action_reference, cycle.amount, cycle.actioned_on = ref, paid, actioned_on
        move_record(sm.MAINTENANCE, cycle, "record_action", sm.ATTORNEY, actor,
                    application=app,
                    extra_fields=("action_reference", "amount", "actioned_on"))
        FinancialRecord.objects.create(application=app, maintenance_cycle_id=cycle.pk,
                                       kind="maintenance_payment", amount=paid,
                                       authorization_level="attorney_recorded",
                                       availability=bd.NOT_AVAILABLE,
                                       recorded_by_user_id=actor.user_id, reference=ref)
        schedule_next(app, after=cycle.due_on)
    return cycle


@ruled
def reassign_decider(*, actor, cycle_id: int, director_user_id: int) -> MaintenanceCycle:
    """Ruling C19: only once the original Director has left the roster."""
    require(actor, P_REASSIGN)
    with transaction.atomic():
        app, cycle = _locked_cycle(actor, cycle_id)
        sm.MAINTENANCE.resolve(cycle.status, "reassign_decider", sm.PCC_ADMIN)
        if conflicted(actor, app):
            raise PermissionDeniedError("You are the applicant or an inventor on this patent.",
                                        code="pcc_admin_conflicted")
        current = cycle.deciding_director_user_id
        if current is not None and candidates.is_active_director(current):
            raise ConflictError("The Director asked to decide is still on the roster.",
                                code="decider_active")
        if not candidates.is_active_director(director_user_id) or director_user_id in (
                app.applicant_user_id,
                *[u for u in app.inventors.values_list("user_id", flat=True) if u]):
            raise ConflictError("Choose an active Director who is not an applicant or "
                                "inventor on this patent.", code="director_not_eligible")
        cycle.deciding_director_user_id = director_user_id
        move_record(sm.MAINTENANCE, cycle, "reassign_decider", sm.PCC_ADMIN, actor,
                    application=app, extra_fields=("deciding_director_user_id",))
        escalations.resolve_open(app, ("inactive_renewal_director",), actor,
                                 "Renewal decision reassigned.")
        notifications.enqueue(
            topic="renewal.requested", dedupe_key=f"renewal.reassigned:{cycle.pk}:"
                                                  f"{director_user_id}",
            recipient_user_id=director_user_id, subject=f"Renewal decision due: {app.reference}",
            body=f"Decide Renew or Do Not Renew for {app.reference} by "
                 f"{cycle.due_on.isoformat()}.")
    return cycle
