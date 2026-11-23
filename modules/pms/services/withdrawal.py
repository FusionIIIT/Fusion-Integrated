"""Withdrawing an application before filing (UC-PMS-006; BR-PMS-067..070)."""
from __future__ import annotations

from django.db import transaction

from modules.pms.domain import state_machine as sm
from modules.pms.domain import validation
from modules.pms.domain import withdrawal as wd
from modules.pms.domain.errors import InvalidInput
from modules.pms.models import Withdrawal, WithdrawalConsent
from modules.pms.selectors import policy as policy_selector
from modules.pms.selectors import scoping
from modules.pms.services import notifications
from modules.pms.services.base import lock, move, move_record, owner_only, require, ruled

P_WITHDRAW = "pms.withdrawal.create"


@ruled
def withdraw(*, actor, pk: int, reason: str, consented_inventor_ids) -> Withdrawal:
    require(actor, P_WITHDRAW)
    spec = policy_selector.current()
    with transaction.atomic():
        app = lock(scoping.applications_for(actor), pk)
        owner_only(actor, app)
        wd.check_allowed(app.status, spec.withdrawal_statuses)
        sm.APPLICATION.resolve(app.status, "withdraw", sm.APPLICANT)
        text = validation.check_withdrawal_reason(reason)
        co_inventors = {i.pk: i for i in app.inventors.all()
                        if i.user_id != app.applicant_user_id}
        consented = set(consented_inventor_ids or [])
        if consented - set(co_inventors):
            raise InvalidInput("Consent can only be recorded for this application's "
                               "co-inventors.", code="unknown_inventor")
        wd.check_consent(spec.withdrawal_consent_required, co_inventors, consented)
        record = Withdrawal.objects.create(application=app, from_status=app.status,
                                           reason=text, withdrawn_by_user_id=actor.user_id)
        WithdrawalConsent.objects.bulk_create(
            WithdrawalConsent(withdrawal=record, inventor=co_inventors[i])
            for i in sorted(consented))
        recipients = [spec.pcc_contact_user_id]
        for cycle in app.review_cycles.select_for_update().filter(status="open"):
            cycle.status = "closed"
            cycle.save(update_fields=["status", "updated_at"])
            recipients.append(cycle.director_user_id)
        for offer in app.attorney_assignments.select_for_update().filter(status=sm.OFFERED):
            move_record(sm.ASSIGNMENT, offer, "cancel", sm.SYSTEM, actor, application=app)
            recipients.append(offer.attorney_user_id)
        for budget in app.budgets.select_for_update().filter(status__in=sorted(sm.OPEN_BUDGET)):
            move_record(sm.BUDGET, budget, "close", sm.SYSTEM, actor, application=app)
        move(app, "withdraw", sm.APPLICANT, actor, details={"withdrawal_id": record.pk})
        notifications.enqueue_many(
            topic="application.withdrawn", key=f"withdrawn:{app.pk}",
            recipients=[app.applicant_user_id, *recipients],
            subject=f"{app.reference} withdrawn",
            body=f"Application {app.reference} was withdrawn by its applicant.")
    return record
