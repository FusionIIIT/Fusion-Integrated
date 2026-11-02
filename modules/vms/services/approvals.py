"""Host decisions on visit requests, early termination, self-service.

VMS-BR-007  notifications about a decision keep the original request id.
VMS-BR-008  a visitor may only interact with their own visit.
VMS-BR-014  approval-timeout reminders are sent on the configured schedule.
VMS-BR-026  a disabled host's check-in is not valid (checked at the gate).
VMS-BR-027  rejecting a visit request disables the visitor.
VMS-BR-047  no host notification when the pass/request is rejected — the
            host made that decision; the visitor is the one informed.
"""
from __future__ import annotations

from django.utils import timezone

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.vms.models import Pass, Visit, VisitRequest, Visitor, VmsNotification
from modules.vms.services import notifications, policies
from modules.vms.services.errors import VmsError
from modules.vms.services.passes import deactivate_pass, issue_pass


def _require_pending(request: VisitRequest) -> None:
    if request.status != "PENDING":
        raise ConflictError(
            f"Request is {request.status}, not pending.",
            code="invalid_request_state",
            details=[{"status": request.status}])


def approve_request(visit_request: VisitRequest, *, actor,
                    notes: str = "",
                    zones: list[str] | None = None,
                    instructions: str = "") -> tuple[VisitRequest, Pass, list]:
    """Host approves: visit scheduled, pass issued, visitor informed."""
    _require_pending(visit_request)
    visitor = Visitor.objects.get(pk=visit_request.visitor_id)
    if visitor.is_disabled:
        raise VmsError("This visitor is disabled.", code="visitor_disabled",
                       status_code=403)

    now = timezone.now()
    visit_request.status = "APPROVED"
    visit_request.decision_at = now
    visit_request.decided_by_user_id = getattr(actor, "user_id", None)
    visit_request.decision_notes = notes
    if instructions:
        visit_request.instructions = instructions
    if zones is not None:
        visit_request.requested_zones = list(zones)
    visit_request.save(update_fields=[
        "status", "decision_at", "decided_by_user_id", "decision_notes",
        "instructions", "requested_zones", "updated_at"])

    visit = Visit.objects.create(
        visit_request_id=visit_request.id, visitor_id=visitor.id,
        host_user_id=visit_request.host_user_id,
        purpose=visit_request.purpose, status="SCHEDULED",
        source=visit_request.source,
        scheduled_start=visit_request.requested_start,
        scheduled_end=visit_request.requested_end,
        created_by_user_id=getattr(actor, "user_id", None))
    pass_obj = issue_pass(
        visit_id=visit.id, visitor_id=visitor.id,
        pass_type="PRE_REGISTERED",
        permitted_zones=list(visit_request.requested_zones),
        issued_by_user_id=getattr(actor, "user_id", None))

    notes_out = notifications.notify_visitor(
        visitor, kind="PASS_ISSUED", subject="Your visit is approved",
        payload={"pass_code": pass_obj.pass_code},
        visit_request=visit_request)
    return visit_request, pass_obj, [n for n in (notes_out,) if n]


def reject_request(visit_request: VisitRequest, *, actor,
                   reason: str) -> VisitRequest:
    _require_pending(visit_request)
    now = timezone.now()
    visit_request.status = "REJECTED"
    visit_request.decision_at = now
    visit_request.decided_by_user_id = getattr(actor, "user_id", None)
    visit_request.rejection_reason = reason
    visit_request.save(update_fields=[
        "status", "decision_at", "decided_by_user_id", "rejection_reason",
        "updated_at"])

    # VMS-BR-027: a denied visit disables the visitor.
    Visitor.objects.filter(pk=visit_request.visitor_id).update(
        is_disabled=True, disabled_reason=f"Visit denied: {reason}")

    # VMS-BR-047: NO host notification — the host just decided. The
    # visitor (safe-list gated, VMS-BR-037) is the one informed.
    visitor = Visitor.objects.get(pk=visit_request.visitor_id)
    notifications.notify_visitor(
        visitor, kind="HOST_DECISION", subject="Visit request rejected",
        payload={"decision": "rejected", "reason": reason},
        visit_request=visit_request)
    return visit_request


def expire_overdue_requests(*, now=None) -> list[VisitRequest]:
    """Pending requests past the approval window auto-expire (baseline
    default 24 hours)."""
    now = now or timezone.now()
    overdue = list(VisitRequest.objects.filter(
        status="PENDING", approval_expires_at__lt=now))
    for request in overdue:
        request.status = "EXPIRED"
        request.save(update_fields=["status", "updated_at"])
    return overdue


def send_timeout_reminders(*, now=None) -> list:
    """VMS-BR-014: the informed timeout — one APPROVAL_TIMEOUT notification
    per request, on the configured reminder schedule, never twice."""
    now = now or timezone.now()
    sent = []
    pending = VisitRequest.objects.filter(status="PENDING").order_by("id")
    for request in pending:
        submitted = request.created_at
        if now < policies.reminder_at(submitted):
            continue
        already = VmsNotification.objects.filter(
            related_visit_request_id=request.id, kind="APPROVAL_TIMEOUT",
            request_id=request.original_request_id).exists()
        if already:
            continue
        sent.extend(notifications.notify_approval_timeout(request))
    return sent


def terminate_visit(visit: Visit, *, actor, reason: str) -> Visit:
    """Host/Admin early termination: pass deactivated, visit closed.

    The deactivation itself sends no host notification (VMS-BR-047).
    """
    if visit.status in ("COMPLETED", "TERMINATED"):
        raise ConflictError(
            f"Visit is already {visit.status}.",
            code="invalid_visit_state",
            details=[{"status": visit.status}])
    active = Pass.objects.filter(visit_id=visit.id, status="ACTIVE").first()
    if active:
        deactivate_pass(active, reason=reason,
                        actor_user_id=getattr(actor, "user_id", None))
    visit.status = "TERMINATED"
    visit.early_terminated = True
    visit.terminated_by_user_id = getattr(actor, "user_id", None)
    visit.termination_reason = reason
    visit.checked_out_at = visit.checked_out_at or timezone.now()
    visit.save(update_fields=["status", "early_terminated",
                              "terminated_by_user_id", "termination_reason",
                              "checked_out_at", "updated_at"])
    return visit


def assert_visitor_owns(principal, visit: Visit) -> None:
    """VMS-BR-008: a visitor may only interact with their own visit."""
    visitor = Visitor.objects.filter(pk=visit.visitor_id).first()
    principal_id = getattr(principal, "user_id", None)
    if visitor is None or visitor.user_id is None:
        raise PermissionDeniedError(
            "This visit has no linked visitor account.",
            code="visit_not_linked")
    if principal_id != visitor.user_id:
        raise PermissionDeniedError(
            "You may only act on your own visit.",
            code="not_your_visit",
            details=[{"visit_id": visit.id}])


def visitor_self_checkout(visit: Visit, *, principal) -> Visit:
    """VMS-BR-008 then the normal checkout path (VMS-BR-023 etc.)."""
    from modules.vms.services import gate

    assert_visitor_owns(principal, visit)
    return gate.check_out(visit=visit, actor=principal, self_service=True)
