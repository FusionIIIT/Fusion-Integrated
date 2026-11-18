"""Approval decisions and substitute response; all writes are audited and atomic."""
from django.db import transaction
from django.utils import timezone
from modules.elm.domain.policy import PolicyViolation
from modules.elm.domain.state_machine import transition as require_transition
from modules.elm.models import LeaveRequest, LeaveTransition
from modules.elm.services import ledger, notifications

PENDING = {"awaiting_substitute", "substitute_declined", "awaiting_unit_head", "awaiting_establishment", "awaiting_sanction", "awaiting_director", "cancellation_pending"}


def _record(req, old, event, actor_user_id, actor_role, note=""):
    LeaveTransition.objects.create(request=req, from_status=old, to_status=req.status, event=event,
        actor_user_id=actor_user_id, actor_role=actor_role or "", note=note)


def _notify_next(req):
    if req.status in PENDING:
        notifications.notify(topic="leave_action_required", title="Leave request awaiting action",
            body=f"Leave request #{req.pk} requires action.", role=req.current_role,
            payload={"request_id": req.pk, "status": req.status})


@transaction.atomic
def respond_substitute(*, request_id: int, actor_user_id: int, accept: bool, note: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id)
    if req.substitute_user_id != actor_user_id or req.status != "awaiting_substitute" or req.substitute_status != "pending":
        raise PolicyViolation("substitute_action_forbidden", "This request is not awaiting your substitute response.")
    first = req.route[0] if req.route else {"role": "Unit Head", "kind": "review"}
    substitute_event = ("substitute_accept_director" if accept and first.get("kind") == "self_sanction"
                        else "substitute_accept" if accept else "substitute_decline")
    require_transition(req.status, substitute_event, "substitute")
    old = req.status
    if not accept:
        req.status, req.substitute_status, req.current_role = "substitute_declined", "declined", "Employee"
        req.save(update_fields=["status", "substitute_status", "current_role", "updated_at"])
        _record(req, old, "substitute_decline", actor_user_id, "substitute", note)
        notifications.notify(topic="substitute_declined", title="Substitute declined", body=f"Your leave request #{req.pk} needs a replacement substitute or withdrawal.", user_id=req.user_id, payload={"request_id": req.pk})
        return req
    req.substitute_status = "accepted"
    req.status = "awaiting_director" if first.get("kind") == "self_sanction" else ("awaiting_unit_head" if first.get("kind") == "review" else "awaiting_sanction")
    req.current_role = first["role"]
    req.stage = 0
    req.save(update_fields=["substitute_status", "status", "current_role", "stage", "updated_at"])
    _record(req, old, substitute_event, actor_user_id, "substitute", note)
    _notify_next(req)
    return req


@transaction.atomic
def nominate_replacement(*, request_id: int, actor_user_id: int, substitute_user_id: int) -> LeaveRequest:
    from modules.elm.services.requests import validate
    req = LeaveRequest.objects.select_for_update().get(pk=request_id, user_id=actor_user_id, status="substitute_declined")
    # Reuse validation to enforce employee identity and availability without charging a new request.
    validate(user_id=req.user_id, category=req.category, start_date=req.start_date, end_date=req.end_date,
             half=req.half, substitute_user_id=substitute_user_id, evidence=req.evidence, exclude_request_id=req.pk)
    require_transition(req.status, "nominate_replacement", "employee")
    old = req.status
    req.substitute_user_id = substitute_user_id
    req.substitute_status = "pending"
    req.status = "awaiting_substitute"
    req.current_role = "Substitute"
    req.save(update_fields=["substitute_user_id", "substitute_status", "status", "current_role", "updated_at"])
    _record(req, old, "nominate_replacement", actor_user_id, "employee")
    notifications.notify(topic="substitute_request", title="Substitute response requested", body=f"Please respond to leave request #{req.pk}.", user_id=substitute_user_id, payload={"request_id": req.pk})
    return req


@transaction.atomic
def decide(*, request_id: int, actor_user_id: int, actor_roles: list[str], decision: str, note: str = "") -> LeaveRequest:
    req = LeaveRequest.objects.select_for_update().get(pk=request_id)
    role_set = set(actor_roles or [])
    if req.status not in PENDING and req.status != "cancellation_pending":
        raise PolicyViolation("request_not_pending", "This request is not awaiting a decision.")
    if req.current_role and req.current_role not in role_set and "Leave Administrator" not in role_set:
        raise PolicyViolation("wrong_reviewer", "This request is not assigned to your current designation.")
    old = req.status
    if req.status == "cancellation_pending":
        require_transition(req.status, "cancellation_approve" if decision == "approve" else "cancellation_reject")
    elif req.status == "awaiting_director":
        require_transition(req.status, "director_self_sanction")
    elif req.status == "awaiting_unit_head":
        event = "unit_reject" if decision in {"reject", "not_recommended"} else ("unit_approve" if req.category in {"CL", "RH"} else "unit_recommend")
        require_transition(req.status, event)
    elif req.status == "awaiting_establishment":
        require_transition(req.status, "establishment_reject" if decision in {"reject", "not_recommended"} else "establishment_forward")
    elif req.status == "awaiting_sanction":
        require_transition(req.status, "sanction_reject" if decision == "reject" else "sanction_approve")
    if req.status == "cancellation_pending":
        if decision == "approve":
            req.cancellation_stage += 1
            next_step = req.route[req.cancellation_stage] if req.cancellation_stage < len(req.route) else None
            if next_step:
                req.current_role = next_step["role"]
                event = "cancellation_forward"
            else:
                req.status, req.current_role = "cancelled", ""
                ledger.reverse_request_debit(req, "reversal")
                event = "cancellation_approve"
        elif decision == "reject":
            req.status, req.current_role = "approved", ""
            event = "cancellation_reject"
        else:
            raise PolicyViolation("invalid_decision", "Decision must be approve or reject.")
    elif req.status == "awaiting_director":
        if "Director" not in role_set or req.user_id != actor_user_id or decision != "approve":
            raise PolicyViolation("director_self_sanction_only", "Only the Director may self-sanction their own leave request.")
        req.status, req.current_role, req.decided_at = "approved", "", timezone.now()
        event = "director_self_sanction"
    elif req.status == "awaiting_unit_head":
        if req.user_id == actor_user_id:
            raise PolicyViolation("self_review_forbidden", "A Unit Head cannot review their own leave request; no alternate route is configured.")
        if decision == "reject" or decision == "not_recommended":
            req.status, req.current_role = "rejected", ""
            req.decided_at = timezone.now()
            req.recommendation = "not_recommended"
            event = "unit_reject" if decision == "reject" else "unit_not_recommend"
        elif decision in {"approve", "recommend"}:
            if req.category in {"CL", "RH"}:
                req.status, req.current_role, req.decided_at = "approved", "", timezone.now()
                req.recommendation = "recommended"
                event = "unit_approve"
            else:
                req.recommendation = "recommended"
                req.stage = max(req.stage + 1, 1)
                next_step = req.route[req.stage] if req.stage < len(req.route) else None
                if next_step:
                    req.status = "awaiting_establishment" if "Establishment" in next_step["role"] or "Deputy Registrar" in next_step["role"] else "awaiting_sanction"
                    req.current_role = next_step["role"]
                else:
                    req.status, req.current_role, req.decided_at = "approved", "", timezone.now()
                event = "unit_recommend"
        else:
            raise PolicyViolation("invalid_decision", "Decision must be approve, recommend, reject, or not_recommended.")
    elif req.status == "awaiting_establishment":
        if decision in {"reject", "not_recommended"}:
            req.status, req.current_role, req.decided_at = "rejected", "", timezone.now()
            event = "establishment_reject"
        elif decision in {"forward", "recommend", "approve"}:
            req.stage += 1
            next_step = req.route[req.stage] if req.stage < len(req.route) else None
            if next_step:
                req.status, req.current_role = "awaiting_sanction", next_step["role"]
            else:
                req.status, req.current_role, req.decided_at = "approved", "", timezone.now()
            event = "establishment_forward"
        else:
            raise PolicyViolation("invalid_decision", "Decision must be forward or reject.")
    elif req.status == "awaiting_sanction":
        if decision == "reject":
            req.status, req.current_role, req.decided_at = "rejected", "", timezone.now()
            event = "sanction_reject"
        elif decision == "approve":
            req.stage += 1
            next_step = req.route[req.stage] if req.stage < len(req.route) else None
            if next_step:
                req.status = "awaiting_establishment" if "Establishment" in next_step["role"] or "Deputy Registrar" in next_step["role"] else "awaiting_sanction"
                req.current_role = next_step["role"]
            else:
                req.status, req.current_role, req.decided_at = "approved", "", timezone.now()
            event = "sanction_approve"
        else:
            raise PolicyViolation("invalid_decision", "Decision must be approve or reject.")
    else:
        raise PolicyViolation("workflow_not_supported", f"No decision action is defined for {req.status}.")
    req.decision_note = note
    req.save()
    _record(req, old, event, actor_user_id, ",".join(actor_roles or []), note)
    if event == "cancellation_reject":
        notifications.notify(topic="leave_cancellation_rejected", title="Cancellation not approved", body=f"Cancellation of leave request #{req.pk} was rejected; the original approval remains in force.", user_id=req.user_id, payload={"request_id": req.pk})
    elif req.status == "cancelled":
        notifications.notify(topic="leave_cancelled", title="Leave cancelled", body=f"Leave request #{req.pk} was cancelled.", user_id=req.user_id, payload={"request_id": req.pk})
    elif req.status == "approved":
        ledger.post_request_debit(req)
        notifications.notify(topic="leave_approved", title="Leave approved", body=f"Leave request #{req.pk} was approved.", user_id=req.user_id, payload={"request_id": req.pk})
    elif req.status == "rejected":
        notifications.notify(topic="leave_rejected", title="Leave not approved", body=f"Leave request #{req.pk} was rejected.", user_id=req.user_id, payload={"request_id": req.pk})
    else:
        _notify_next(req)
    return req
