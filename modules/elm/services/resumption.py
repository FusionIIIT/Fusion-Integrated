from datetime import date
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from modules.elm.domain.policy import PolicyViolation
from modules.elm.domain.state_machine import transition as require_transition
from modules.elm.models import LeaveRequest, LeaveTransition
from modules.elm.services import ledger, notifications

@transaction.atomic
def submit(*, request_id: int, actor_user_id: int, actual_return_date: date, note: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id, user_id=actor_user_id, status="approved", kind="leave")
    if req.category not in {"EL", "COL", "VL"}:
        raise PolicyViolation("resumption_not_required", "Resumption records apply to EL, COL, and VL.")
    effective_end = max([req.end_date, *req.extensions.filter(status="approved").values_list("end_date", flat=True)])
    if actual_return_date > timezone.localdate():
        raise PolicyViolation("future_return_date", "Resumption can only be submitted on or after the actual return date.")
    if actual_return_date < req.start_date:
        raise PolicyViolation("invalid_return_date", "Actual return date cannot precede the leave start date.")
    if actual_return_date < effective_end:
        kind = "early"
    elif actual_return_date > effective_end:
        kind = "late"
    else:
        kind = "normal"
    require_transition(req.status, "submit_resumption", "employee")
    old = req.status
    req.status = "resumption_pending"
    req.actual_return_date = actual_return_date
    req.resumption_kind = kind
    req.resumption_note = note
    req.current_role = req.route[-1]["role"] if req.route else "Leave Administrator"
    req.save()
    LeaveTransition.objects.create(request=req, from_status=old, to_status=req.status, event="submit_resumption", actor_user_id=actor_user_id, note=note, data={"kind": kind, "actual_return_date": actual_return_date.isoformat()})
    notifications.notify(topic="resumption_review", title="Resumption requires verification", body=f"Resumption for leave request #{req.pk} needs verification.", role=req.current_role, payload={"request_id": req.pk})
    return req

@transaction.atomic
def verify(*, request_id: int, actor_user_id: int, actor_roles: list[str], note: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(
        pk=request_id, status="resumption_pending")
    role_set = set(actor_roles or [])
    if req.current_role and req.current_role not in role_set and "Leave Administrator" not in role_set:
        raise PolicyViolation("wrong_reviewer", "This resumption is not assigned to your designation.")

    require_transition(req.status, f"verify_resumption_{req.resumption_kind}")
    old = req.status
    segments = [req, *req.extensions.filter(status="approved").order_by("start_date")]
    effective_end = max(segment.end_date for segment in segments)
    if req.resumption_kind == "normal":
        outcome = "resumption_reviewed_no_adjustment"
        # Normal resumption records the review only: approved dates and balances
        # are intentionally unchanged.
    elif req.resumption_kind == "early":
        outcome = "resumption_reviewed_early"
        total_actual = Decimal("0")
        for segment in segments:
            if req.actual_return_date >= segment.end_date:
                unused = Decimal("0")
            elif req.actual_return_date < segment.start_date:
                unused = segment.days
            else:
                unused = min(segment.days, Decimal((segment.end_date - req.actual_return_date).days))
            total_actual += max(Decimal("0"), segment.days - unused)
            if unused > 0:
                ledger.LedgerEntry.objects.get_or_create(
                    request=segment, entry_type="restore",
                    defaults={"user_id": segment.user_id, "category": segment.category,
                              "year": segment.start_date.year, "delta": unused,
                              "note": "Unused leave restored after verified early return"})
            if req.actual_return_date < segment.start_date:
                # This segment was never consumed; preserve its originally
                # sanctioned dates while its reviewed outcome removes it from
                # active leave and the ledger restores the full segment.
                pass
            elif req.actual_return_date < segment.end_date:
                segment.end_date = req.actual_return_date
                segment.days = max(Decimal("0.01"), segment.days - unused)
            if segment != req:
                segment.status = outcome
                segment.current_role = ""
                segment.actual_return_date = req.actual_return_date
                segment.decided_at = timezone.now()
                segment.save(update_fields=["status", "current_role", "actual_return_date", "decided_at", "updated_at", "end_date", "days"])
                LeaveTransition.objects.create(
                    request=segment, from_status="approved", to_status=outcome,
                    event="resumption_sync_from_parent", actor_user_id=actor_user_id,
                    actor_role=",".join(actor_roles or []), note=note,
                    data={"actual_return_date": req.actual_return_date.isoformat()})
        req.days = max(Decimal("0.01"), total_actual)
        req.end_date = req.actual_return_date
    else:
        outcome = "resumption_reviewed_late"
        extra = Decimal((req.actual_return_date - effective_end).days)
        if extra > 0:
            ledger.LedgerEntry.objects.get_or_create(
                request=req, entry_type="adjustment",
                defaults={"user_id": req.user_id, "category": req.category,
                          "year": req.start_date.year, "delta": -extra,
                          "note": "Additional leave debited after verified late return"})
        req.days = sum((segment.days for segment in segments), Decimal("0")) + extra
        req.end_date = req.actual_return_date
        for segment in segments[1:]:
            segment.status = outcome
            segment.current_role = ""
            segment.actual_return_date = req.actual_return_date
            segment.decided_at = timezone.now()
            segment.save(update_fields=["status", "current_role", "actual_return_date", "decided_at", "updated_at"])
            LeaveTransition.objects.create(
                request=segment, from_status="approved", to_status=outcome,
                event="resumption_sync_from_parent", actor_user_id=actor_user_id,
                actor_role=",".join(actor_roles or []), note=note,
                data={"actual_return_date": req.actual_return_date.isoformat()})

    req.status, req.current_role, req.decided_at = outcome, "", timezone.now()
    if note:
        req.resumption_note = (req.resumption_note + "\n" + note).strip()
    req.save()
    LeaveTransition.objects.create(
        request=req, from_status=old, to_status=outcome,
        event=f"verify_resumption_{req.resumption_kind}", actor_user_id=actor_user_id,
        actor_role=",".join(actor_roles or []), note=note,
        data={"kind": req.resumption_kind,
              "actual_return_date": req.actual_return_date.isoformat() if req.actual_return_date else None})
    notifications.notify(topic="resumption_verified", title="Resumption verified",
        body=f"Resumption for leave request #{req.pk} was verified.", user_id=req.user_id,
        payload={"request_id": req.pk, "outcome": outcome})
    return req
