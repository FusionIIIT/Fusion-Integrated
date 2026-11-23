"""Patent-office communications, including grants and refusals (UC-PMS-014; ruling C9)."""
from __future__ import annotations

from datetime import date

from django.db import transaction

from core.api.exceptions import ConflictError
from modules.pms.domain import state_machine as sm
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Communication, OfficeAction
from modules.pms.selectors import scoping
from modules.pms.services import audit, maintenance, notifications
from modules.pms.services.base import accepted_attorney_only, lock, move, require, ruled, today

P_RECORD = "pms.communication.create"
KINDS = ("office_action", "grant", "refusal", "other")


@ruled
def record(*, actor, pk: int, kind: str, received_on: date, reference: str, details: str = "",
           response_due_on: date | None = None, requires_applicant_review: bool = False,
           grant_date: date | None = None, patent_number: str = "",
           jurisdiction: str = "") -> Communication:
    require(actor, P_RECORD)
    if kind not in KINDS:
        raise InvalidInput("Choose office action, grant, refusal or other.",
                           code="invalid_kind")
    ref = (reference or "").strip()
    if not ref or len(ref) > 200:
        raise InvalidInput("Give the communication's reference number.",
                           code="reference_required")
    if received_on > today():
        raise InvalidInput("The received date cannot be in the future.", code="date_in_future")
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        accepted_attorney_only(actor, app)
        allowed = (sm.FILED,) if kind in ("office_action", "grant", "refusal") \
            else (sm.FILED, sm.GRANTED)
        if app.status not in allowed:
            raise ConflictError("That communication can be recorded only while the "
                                "application is " + " or ".join(allowed) + ".",
                                code="communication_not_allowed")
        if kind == "grant":
            juris = (jurisdiction or "").strip().upper()
            number = (patent_number or "").strip()
            if grant_date is None or grant_date > today():
                raise InvalidInput("Give the grant date, which cannot be in the future.",
                                   code="grant_date_required")
            if not number or len(number) > 64:
                raise InvalidInput("Give the granted patent's number.",
                                   code="patent_number_required")
            if not app.filings.filter(jurisdiction=juris).exists():
                raise InvalidInput("The grant must be in a jurisdiction where the application "
                                   "was filed.", code="jurisdiction_not_filed")
        comm = Communication.objects.create(application=app, kind=kind,
                                            received_on=received_on, reference=ref,
                                            details=(details or "").strip()[:20_000],
                                            recorded_by_user_id=actor.user_id)
        audit.record(actor, f"communication.{kind}", application=app, obj=comm)
        if kind == "office_action":
            oa = OfficeAction.objects.create(communication=comm, application=app,
                                             response_due_on=response_due_on,
                                             requires_applicant_review=bool(
                                                 requires_applicant_review))
            notifications.enqueue(
                topic="office_action.recorded", dedupe_key=f"office_action:{oa.pk}",
                recipient_user_id=app.applicant_user_id,
                subject=f"Office action on {app.reference}",
                body=f"The patent office issued an office action ({ref}) on {app.reference}."
                     + (f" The response is due by {response_due_on.isoformat()}."
                        if response_due_on else ""))
        elif kind == "grant":
            app.grant_date, app.patent_number, app.grant_jurisdiction = grant_date, number, juris
            move(app, "grant", sm.ATTORNEY, actor, details={"communication_id": comm.pk},
                 extra_fields=("grant_date", "patent_number", "grant_jurisdiction"))
            maintenance.activate(app)
            notifications.enqueue(
                topic="application.status", dedupe_key=f"granted:{app.pk}",
                recipient_user_id=app.applicant_user_id, subject=f"Granted: {app.reference}",
                body=f"{app.reference} was granted as patent {number}.")
        elif kind == "refusal":
            move(app, "refuse", sm.ATTORNEY, actor, details={"communication_id": comm.pk})
            notifications.enqueue(
                topic="application.status", dedupe_key=f"refused:{app.pk}",
                recipient_user_id=app.applicant_user_id, subject=f"Refused: {app.reference}",
                body=f"The patent office refused {app.reference} ({ref}).")
    return comm
