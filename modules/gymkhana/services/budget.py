"""Club budget requests (UC-GYM-009): submitted and kept open for tracking only."""
from __future__ import annotations

from decimal import Decimal

from django.db import transaction

from core.api.exceptions import DomainError, NotFoundError
from modules.gymkhana.domain import rules
from modules.gymkhana.domain.rules import RuleViolation
from modules.gymkhana.models import BudgetRequest
from modules.gymkhana.selectors import scoping
from modules.gymkhana.services import audit, links
from modules.gymkhana.services.authz import require
from modules.gymkhana.services.errors import refused

P_SUBMIT = "gymkhana.budget_request.create"


def _text(value: str, field: str, message: str) -> str:
    text = (value or "").strip()
    if not text:
        raise DomainError(message, code="missing_field",
                          details=[{"field": field, "message": message}])
    return text


@transaction.atomic
def submit(*, actor, club_id: int, purpose: str, description: str, amount: Decimal,
           document_url: str) -> BudgetRequest:
    require(actor, P_SUBMIT)
    club = scoping.led_clubs(actor).filter(pk=club_id).first()
    if club is None:
        raise NotFoundError("No such club among the clubs you lead.")
    purpose = _text(purpose, "purpose", "Enter the purpose of the budget.")
    description = _text(description, "description", "Describe the budget request.")
    try:
        rules.check_amount(amount)
    except RuleViolation as exc:
        raise refused(exc) from exc
    document = links.parse_link(
        document_url, field="document_url", missing_code="supporting_file_required",
        missing_message="A budget request needs its supporting document. Paste the "
                        "Google Drive link to it.")
    request = BudgetRequest.objects.create(
        club=club, purpose=purpose, description=description, amount=amount,
        document_link=document.url, document_file_id=document.file_id,
        status=BudgetRequest.OPEN, submitted_by_user_id=actor.user_id)
    audit.record("budget_request.submitted", object_type="budget_request",
                 object_id=request.pk, actor=actor, club_id=club.pk)
    return request
