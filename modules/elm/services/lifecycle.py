"""After approval: cancellation, extension, resumption (WF-EL-03, 04, 05)."""
from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import PermissionDeniedError
from modules.elm.domain import leave_types as lt
from modules.elm.domain import workflow as wf
from modules.elm.domain.errors import RuleViolation
from modules.elm.models import LeaveApplication
from modules.elm.selectors import applications as sel
from modules.elm.selectors import queues
from modules.elm.services import applications, balances
from modules.elm.services.common import (
    announce_task,
    enforcing_rules,
    load,
    move,
    notify,
    require_owner,
    require_permission,
    require_status,
)


@transaction.atomic
def request_cancellation(principal, pk: int, *, reason: str = "") -> LeaveApplication:
    """BR-EL-023: only before the leave begins, through the same hierarchy as the original."""
    application = load(pk)
    require_owner(principal, application)
    require_status(application, wf.APPROVED)
    with enforcing_rules():
        if application.start_date <= timezone.localdate():
            raise RuleViolation(
                "This leave has begun; use an extension or resumption instead.", "BR-EL-023")
        if sel.live_extensions(application.pk).exists():
            raise RuleViolation("Cancel the extension first.", "BR-EL-023")
    target = wf.AWAITING_DIRECTOR if application.is_director else wf.AWAITING_UNIT_HEAD
    application.pending_action = "CANCEL"
    application.unit_head_recommendation = ""
    event = move(application, target, action="cancellation_requested",
                 actor_id=principal.user_id, note=reason, role=wf.EMPLOYEE)
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def request_extension(principal, pk: int, data: dict[str, Any]) -> LeaveApplication:
    """BR-EL-025: a separate request, validated and routed like any other."""
    original = load(pk)
    require_owner(principal, original)
    require_status(original, wf.APPROVED)
    today = timezone.localdate()
    new_end = data["end_date"]
    with enforcing_rules():
        if original.leave_type not in lt.EXTENDABLE:
            raise RuleViolation("Only EL, COL and VL can be extended.", "BR-EL-025")
        if not original.start_date <= today <= original.end_date:
            raise RuleViolation("Only a leave that is under way can be extended.", "BR-EL-025")
        if sel.live_extensions(original.pk).exists():
            raise RuleViolation("An extension is already in progress.", "BR-EL-025")
        if new_end <= original.end_date:
            raise RuleViolation("The new end date must be after the current end.", "BR-EL-025")
    request = {
        "leave_type": original.leave_type, "start_date": original.end_date + timedelta(days=1),
        "end_date": new_end, "half_day": lt.NO_HALF,
        "special_purpose": data.get("special_purpose", original.special_purpose),
        "medical_reference": data.get("medical_reference", original.medical_reference),
        "station_leave": original.station_leave, "station_address": original.station_address,
        "substitute_user_id": data.get("substitute_user_id"),
    }
    return applications.submit(principal, request, extends=original)


@transaction.atomic
def submit_resumption(principal, pk: int, *, resumed_on: date) -> LeaveApplication:
    """BR-EL-027/028: report back through ELM; the leave is closed on verification."""
    application = load(pk)
    require_owner(principal, application)
    require_status(application, wf.APPROVED)
    with enforcing_rules():
        if application.leave_type not in lt.EXTENDABLE:
            raise RuleViolation("Resumption applies to EL, COL and VL.", "BR-EL-027")
        if resumed_on < application.start_date:
            raise RuleViolation("You cannot resume before the leave started.", "BR-EL-028")
        if resumed_on > timezone.localdate():
            raise RuleViolation("The date of resumption cannot be in the future.", "BR-EL-027")
        if sel.live_extensions(application.pk).exists():
            raise RuleViolation("Resume against the latest extension.", "BR-EL-027")
    application.resumed_on = resumed_on
    event = move(application, wf.RESUMPTION_PENDING, action="resumption_submitted",
                 actor_id=principal.user_id, role=wf.EMPLOYEE)
    application.save()
    announce_task(application, f"ev{event.pk}")
    return application


@transaction.atomic
def verify_resumption(principal, pk: int, *, verified: bool = True) -> LeaveApplication:
    """BR-EL-028: unused days come back only once the return is verified."""
    application = load(pk)
    require_status(application, wf.RESUMPTION_PENDING)
    require_permission(principal, queues.P_REVIEW)
    if application.user_id == principal.user_id:
        raise PermissionDeniedError("You cannot verify your own resumption.")
    if not queues.same_unit(principal.user_id, application.user_id):
        raise PermissionDeniedError("This applicant is not in your unit.")
    if not verified:
        application.resumed_on = None
        event = move(application, wf.APPROVED, action="resumption_not_verified",
                     actor_id=principal.user_id, role=wf.UNIT_HEAD)
        application.save()
        notify(application, "leave.resumption_not_verified", "Your resumption was not verified.",
               user_id=application.user_id, key=f"ev{event.pk}")
        return application
    resumed_on = application.resumed_on
    unused = Decimal(0)
    if resumed_on <= application.end_date:
        unused = min(application.days, Decimal((application.end_date - resumed_on).days + 1))
        balances.restore(application, unused, "Early resumption verified")
    application.restored_days = unused
    application.actual_end_date = min(resumed_on - timedelta(days=1), application.end_date)
    event = move(application, wf.COMPLETED, action="resumption_verified",
                 actor_id=principal.user_id, role=wf.UNIT_HEAD)
    application.save()
    notify(application, "leave.resumption_verified", "Your resumption was verified.",
           user_id=application.user_id, key=f"ev{event.pk}")
    return application
