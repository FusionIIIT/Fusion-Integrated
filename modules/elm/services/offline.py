"""Recording leave already sanctioned on paper (BR-EL-029, WF-EL-06).

This synchronises ELM with a decision made elsewhere. It is not a second
approval, so nothing is routed; it is still validated like any request, because
a record that breaks the balance or overlaps other leave would corrupt ELM.
"""
from __future__ import annotations

from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import NotFoundError
from modules.directory import contracts as directory
from modules.elm.domain import workflow as wf
from modules.elm.domain.errors import RuleViolation
from modules.elm.models import ApplicationSource, LeaveApplication
from modules.elm.services import applications, balances
from modules.elm.services.common import (
    enforcing_rules,
    move,
    notify,
    require_permission,
)

P_ADMINISTER = "elm.leave.administer"


@transaction.atomic
def record(principal, data: dict[str, Any]) -> LeaveApplication:
    require_permission(principal, P_ADMINISTER)
    employee_id = data["user_id"]
    person = directory.get_users([employee_id]).get(employee_id)
    if person is None:
        raise NotFoundError("That employee is not in the directory.")
    with enforcing_rules():
        if not data.get("offline_reference", "").strip():
            raise RuleViolation("Give the reference of the paper sanction.", "BR-EL-029")
        days = applications.validate_request(
            user_id=employee_id, kind=person.kind, data={**data, "substitute_user_id": None})
    fields = applications.fields_of(data)
    fields["substitute_user_id"] = None
    application = LeaveApplication.objects.create(
        user_id=employee_id, applicant_kind=person.kind, days=days,
        status=wf.APPROVED, source=ApplicationSource.OFFLINE,
        offline_reference=data["offline_reference"], recorded_by=principal.user_id,
        decided_by=principal.user_id, decided_at=timezone.now(),
        decision_reason="Sanctioned offline", **fields)
    with enforcing_rules():
        balances.deduct(application)
    event = move(application, wf.APPROVED, action="recorded_offline",
                 actor_id=principal.user_id, note=data["offline_reference"], first=True)
    application.save()
    notify(application, "leave.recorded", "A leave sanctioned on paper was recorded for you.",
           user_id=employee_id, key=f"ev{event.pk}")
    return application
