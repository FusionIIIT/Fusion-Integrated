"""Finance records internal completion (UC-105, UC-404); no money moves (BR-006)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import DomainError
from modules.iaa.domain import roles
from modules.iaa.domain import state_machine as sm
from modules.iaa.models import BudgetEntry, FinancialRecord
from modules.iaa.selectors import scoping
from modules.iaa.services import notify, trail
from modules.iaa.services.authz import require, role_of
from modules.iaa.services.common import domain_errors, lock, now

P_PROCESS = "iaa.processing.create"


@transaction.atomic
def record(actor, pk: int, *, reference: str, note: str = "") -> FinancialRecord:
    require(actor, P_PROCESS)
    if not reference.strip():
        raise DomainError("Enter the internal processing reference (voucher or file number).",
                          code="reference_required")
    item = lock(scoping.records_for(actor), pk)
    with domain_errors():
        t = sm.resolve_record(item.kind, item.status, sm.RECORD,
                              roles.actor_kind(role_of(actor)))
    item.status = t.to
    item.processing_reference, item.processing_note = reference, note
    item.processed_at, item.processed_by = now(), actor.user_id
    item.save()
    if item.financial_year_id is not None:
        BudgetEntry.objects.create(
            financial_year_id=item.financial_year_id, department=item.department,
            kind=BudgetEntry.COMMITMENT, amount=-item.amount, record=item,
            note=f"Recorded #{item.pk} ({reference})", created_by=actor.user_id,
            created_role=role_of(actor))
    trail.log("record", item.pk, "record", actor=actor, frm=t.frm, to=t.to,
              remarks=f"Internal record {reference}. No payment executed. {note}".strip())
    notify.to_user(item.user_id, "recorded",
                   f"#{item.pk} has been recorded by Finance (reference {reference}).",
                   "record", item.pk)
    return item
