"""Recording an external filing (UC-PMS-013; BR-PMS-020, 055, 056, 075, 078, 128, 142)."""
from __future__ import annotations

from datetime import date

from django.db import IntegrityError, transaction

from core.api.exceptions import ConflictError
from modules.pms.domain import filing as fl
from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.domain.errors import InvalidInput, RuleViolation
from modules.pms.models import Filing
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import notifications
from modules.pms.services.base import (
    accepted_attorney_only,
    lock,
    move,
    require,
    ruled,
    today,
)

P_FILE = "pms.filing.create"


def facts(app) -> fl.FilingFacts:
    return fl.FilingFacts(
        has_accepted_attorney=app.attorney_assignments.filter(status=sm.ACCEPTED).exists(),
        has_approved_budget=app.budgets.filter(status__in=sorted(sm.APPROVED_BUDGET)).exists(),
        inventors=tuple(fl.InventorState(i.name, i.agreement_completed_at is not None,
                                         i.consent_recorded_at is not None)
                        for i in app.inventors.order_by("id")))


@ruled
def record_filing(*, actor, pk: int, jurisdiction: str, office_name: str,
                  external_filing_id: str, filing_date: date, confirmation_reference: str,
                  international_justification: str = "") -> Filing:
    require(actor, P_FILE)
    juris = (jurisdiction or "").strip().upper()
    office = (office_name or "").strip()
    if not office or len(office) > 120:
        raise InvalidInput("Name the patent office (at most 120 characters).",
                           code="office_required")
    fl.check_filing(jurisdiction=juris, external_filing_id=external_filing_id,
                    filing_date=filing_date, confirmation_reference=confirmation_reference,
                    today=today())
    justification = validation.check_international_justification(
        juris, international_justification)
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        accepted_attorney_only(actor, app)
        first = app.status == sm.ATTORNEY_ASSIGNED
        if first:
            blockers = fl.filing_blockers(facts(app))
            if blockers:
                raise RuleViolation("Filing is blocked: " + " ".join(blockers),
                                    code="filing_blocked")
        elif app.status not in (sm.FILED, sm.GRANTED):
            raise ConflictError("Filings are recorded once an attorney has accepted the case.",
                                code="filing_not_allowed")
        try:
            with transaction.atomic():
                row = Filing.objects.create(
                    application=app, jurisdiction=juris, office_name=office,
                    international_justification=justification,
                    external_filing_id=external_filing_id.strip(), filing_date=filing_date,
                    confirmation_reference=confirmation_reference.strip()[:200],
                    format_validation=fl.NO_RULES, filed_by_user_id=actor.user_id)
        except IntegrityError as exc:
            raise ConflictError("That patent office application number is already recorded.",
                                code="filing_duplicate") from exc
        if first:
            move(app, "file", sm.ATTORNEY, actor, details={"filing_id": row.pk,
                                                           "jurisdiction": juris})
        spec = policy_selector.current()
        notifications.enqueue_many(
            topic="filing.confirmed", key=f"filing:{row.pk}",
            recipients=[app.applicant_user_id, scoping.reviewing_director_id(app),
                        spec.pcc_contact_user_id],
            subject=f"Filed: {app.reference}",
            body=f"{app.reference} was filed with {office} as {row.external_filing_id} on "
                 f"{filing_date.isoformat()}.")
    return row
