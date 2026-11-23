"""Post-grant maintenance services (UC-PMS-017, UC-PMS-018, BR-PMS-059..061, BR-PMS-100)."""
from __future__ import annotations

import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, DomainError, NotFoundError, PermissionDeniedError
from modules.patents.domain import maintenance as mt
from modules.patents.domain import state_machine as sm
from modules.patents.models import PatentApplication, RenewalHistory
from modules.patents.selectors import scoping
from modules.patents.services import audit, notifications


def _granted_application(actor, application_id: int) -> PatentApplication:
    app = scoping.applications_for(actor).select_for_update().filter(pk=application_id).first()
    if app is None:
        raise NotFoundError("Patent application not found.")
    if app.status != sm.GRANTED:
        raise ConflictError("Maintenance is only applicable to GRANTED patents (BR-PMS-059).")
    return app


def request_renewal_decision(actor, application_id: int, notes: str = "") -> PatentApplication:
    """Attorney asks the Director for a Renew / Do Not Renew decision (BW-PMS-14 step 1)."""
    if not scoping.is_attorney(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Attorney authority required to request a decision.")

    with transaction.atomic():
        app = _granted_application(actor, application_id)
        if app.maintenance_state not in mt.CYCLE_OPEN:
            raise ConflictError("A renewal decision was already requested or made for this cycle.")
        previous = app.maintenance_state or mt.ACTIVE
        app.maintenance_state = mt.DECISION_REQUESTED
        app.renewal_requested_at = timezone.now()
        app.version += 1
        app.save()
        audit.record(
            actor, "renewal_decision_requested", app, previous, app.maintenance_state,
            cycle_due_date=app.renewal_due_date.isoformat() if app.renewal_due_date else "",
            notes=notes,
        )
    notifications.notify(
        [app.assigned_director_id], app, "Renewal decision requested",
        "A maintenance deadline is due: decide Renew or Do Not Renew.",
    )
    return app


def record_renewal_decision(
    actor,
    application_id: int,
    renew: bool,
    notes: str = "",
) -> PatentApplication:
    """Record the Director's explicit Renew / Do Not Renew decision (BR-PMS-061)."""
    if not scoping.is_director(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Director authority required for renewal decision.")

    with transaction.atomic():
        app = _granted_application(actor, application_id)
        if app.maintenance_state not in mt.AWAITING_DECISION:
            raise ConflictError("A renewal decision was already made for this maintenance cycle.")

        previous = app.maintenance_state or mt.ACTIVE
        now = timezone.now()
        # The decision time closes the renewal alert; the record itself is kept in the history.
        app.renewal_decided_at = now
        app.renewal_decision = "RENEW" if renew else "DO_NOT_RENEW"
        app.maintenance_state = mt.RENEWAL_APPROVED if renew else mt.DO_NOT_RENEW
        app.version += 1
        app.save()
        RenewalHistory.objects.create(
            application=app,
            cycle_due_date=app.renewal_due_date,
            requested_at=app.renewal_requested_at,
            decision=app.renewal_decision,
            decided_by_user_id=getattr(actor, "user_id", 0),
            decided_at=now,
        )
        audit.record(
            actor, "renewal_decision", app, previous, app.maintenance_state,
            decision=app.renewal_decision, notes=notes,
        )
    notifications.notify(
        [app.assigned_attorney_id], app, "Renewal decision recorded",
        f"The Director decided: {app.renewal_decision}.",
    )
    return app


def record_maintenance_action(
    actor,
    application_id: int,
    reference: str,
    next_due_date: datetime.date | None = None,
    notes: str = "",
) -> PatentApplication:
    """Attorney records the maintenance action for an approved renewal and schedules the
    next cycle (BW-PMS-14 step 3). Payment itself happens outside PMS.

    PMS holds no jurisdiction schedule rules, so it never invents the next due date: the
    Attorney supplies it, and without one the cycle closes with no next date scheduled
    (BR-PMS-060, BR-PMS-100).
    """
    if not scoping.is_attorney(actor) and not scoping.is_pcc_admin(actor):
        raise PermissionDeniedError("Attorney authority required to record a maintenance action.")
    if not (reference or "").strip():
        raise DomainError(
            "Record the maintenance transaction reference.", code="reference_required",
        )

    with transaction.atomic():
        app = _granted_application(actor, application_id)
        if app.maintenance_state != mt.RENEWAL_APPROVED:
            raise ConflictError("No approved renewal decision to record a maintenance action for.")
        if next_due_date is not None and next_due_date <= timezone.now().date():
            raise DomainError(
                "The next maintenance due date must be in the future.", code="invalid_due_date",
            )

        history = (
            RenewalHistory.objects.select_for_update()
            .filter(application=app, decision="RENEW", action_recorded_at__isnull=True)
            .order_by("-id").first()
        )
        now = timezone.now()
        if history is not None:
            history.action_reference = reference
            history.action_recorded_by_user_id = getattr(actor, "user_id", 0)
            history.action_recorded_at = now
            history.next_due_date = next_due_date
            history.save()

        app.maintenance_state = mt.RENEWED
        app.renewal_due_date = next_due_date
        app.renewal_requested_at = None
        app.renewal_decided_at = None
        app.renewal_decision = ""
        app.version += 1
        app.save()
        audit.record(
            actor, "maintenance_action_recorded", app, mt.RENEWAL_APPROVED, mt.RENEWED,
            reference=reference, notes=notes,
            next_due_date=next_due_date.isoformat() if next_due_date else "",
            next_cycle=(
                "scheduled" if next_due_date else "not scheduled: schedule data required"
            ),
        )
    return app
