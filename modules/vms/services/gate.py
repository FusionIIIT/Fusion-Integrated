"""Gate operations: check-in, check-out, gate close-out, offline entries.

VMS-BR-002  an alert auto-closes on entrance; if that is not effective it
            stays open (HIGH blacklist hits need a human).
VMS-BR-006  closing an already-closed visit is a conflict, never a silent
            second close.
VMS-BR-013  an anonymous visitor's QR is invalid — OTP only.
VMS-BR-018  a walk-in whose pass ran out gets exactly one final extension.
VMS-BR-019  the stay log is closed when the visit ends.
VMS-BR-023  a checkout is not logged when the visit is already complete.
VMS-BR-025  a misconfigured security person invalidates the visit.
VMS-BR-028  a successful validation auto-closes the visitor's alerts.
VMS-BR-029  badge reads for guest operations use the nominal machine id.
VMS-BR-030  a gate close-out needs every visitor checked out.
VMS-BR-040  a failed validation never opens a second alert.
"""
from __future__ import annotations

from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.models import Pass, Visit, VisitLog, Visitor
from modules.vms.services import blacklist as blacklist_service
from modules.vms.services import notifications, policies, roles
from modules.vms.services.alerts import close_alerts_on_entry, open_alert
from modules.vms.services.errors import (
    PassStateError,
    SecurityMisconfiguredError,
)
from modules.vms.services.passes import (
    expire_if_due,
    find_pass,
    pass_is_live,
)
from modules.vms.services.violations import close_on_visibility, raise_violation


def _log(*, visit_id: int, visitor_id: int, event_type: str,
         pass_id: int | None = None, zone_code: str = "",
         gate_code: str = "", machine_id: str = "",
         recorded_by_user_id: int | None = None,
         details: dict | None = None, occurred_at=None,
         offline_cached: bool = False) -> VisitLog:
    return VisitLog.objects.create(
        visit_id=visit_id, visitor_id=visitor_id, event_type=event_type,
        pass_id=pass_id, zone_code=zone_code, gate_code=gate_code,
        machine_id=machine_id, occurred_at=occurred_at or timezone.now(),
        recorded_by_user_id=recorded_by_user_id, details=details or {},
        offline_cached=offline_cached)


def _host_request(visit: Visit):
    if not visit.visit_request_id:
        return None
    from modules.vms.models import VisitRequest
    return VisitRequest.objects.filter(pk=visit.visit_request_id).first()


def check_in(*, pass_code: str, machine_id: str, actor,
             otp: str = "", gate_code: str = "") -> dict:
    policy = policies.effective()
    policies.require_nominal_machine(policy, machine_id)     # BR-029

    pass_obj = find_pass(pass_code)
    if pass_obj is None:
        raise NotFoundError("Pass not found.", code="pass_not_found")
    visitor = Visitor.objects.get(pk=pass_obj.visitor_id)

    # BR-013: an anonymous visitor has no QR identity — OTP only.
    if visitor.is_anonymous and otp != pass_obj.otp:
        raise PassStateError(
            "QR is invalid for an anonymous visitor; use the OTP.",
            code="anonymous_qr_invalid")

    # BR-011: the gate is a blacklist checkpoint.
    blacklist_service.assert_registration_allowed(
        visitor, context="gate check-in")

    visit = Visit.objects.get(pk=pass_obj.visit_id)
    if visit.status == "ON_SITE":
        raise ConflictError("This visit is already checked in.",
                            code="already_checked_in")
    if visit.status in ("COMPLETED", "TERMINATED", "INVALIDATED"):
        raise ConflictError(f"Visit is {visit.status}.",
                            code="invalid_visit_state",
                            details=[{"status": visit.status}])

    roles.require_host_enabled(visit.host_user_id)           # BR-026

    pass_obj = expire_if_due(pass_obj)                       # auto-expire
    if not pass_is_live(pass_obj):
        raise_violation(kind="EXPIRED_PASS", visit_id=visit.id,
                        visitor_id=visitor.id, pass_id=pass_obj.id,
                        details={"machine_id": machine_id})  # BR-003
        open_alert(alert_type="GATE_VALIDATION_FAILURE",
                   severity="MEDIUM",
                   message=f"Expired pass presented at {gate_code or 'gate'}",
                   visitor_id=visitor.id, visit_id=visit.id,
                   pass_id=pass_obj.id)                      # BR-040 dedupe
        raise PassStateError("This pass has expired.",
                             code="pass_expired")

    now = timezone.now()
    actor_id = getattr(actor, "user_id", None)
    try:
        roles.require_security(actor, gate_code=gate_code)   # BR-025
    except SecurityMisconfiguredError as exc:
        # The visit exists; a misconfigured recorder invalidates it.
        visit.status = "INVALIDATED"
        visit.invalidated_reason = str(exc)
        visit.save(update_fields=["status", "invalidated_reason",
                                  "updated_at"])
        raise

    visit.status = "ON_SITE"
    visit.checked_in_at = now
    visit.checked_in_by_user_id = actor_id
    visit.checked_in_machine_id = machine_id
    if gate_code:
        visit.gate_code = gate_code
    visit.save(update_fields=["status", "checked_in_at",
                              "checked_in_by_user_id",
                              "checked_in_machine_id", "gate_code",
                              "updated_at"])

    _log(visit_id=visit.id, visitor_id=visitor.id,
         event_type="CHECK_IN", pass_id=pass_obj.id,
         gate_code=gate_code, machine_id=machine_id,
         recorded_by_user_id=actor_id)                       # entry logged
    _log(visit_id=visit.id, visitor_id=visitor.id,
         event_type="STAY_START", pass_id=pass_obj.id,
         gate_code=gate_code, machine_id=machine_id,
         recorded_by_user_id=actor_id)

    close_alerts_on_entry(visitor.id, visit_id=visit.id,     # BR-002/028
                          actor_user_id=actor_id)
    close_on_visibility(visit.id, actor_user_id=actor_id)    # BR-010

    request = _host_request(visit)
    if request is not None:
        notifications.notify_host(                                 # CFR-012
            request, kind="CHECK_IN", subject="Visitor arrived",
            payload={"visit_id": visit.id,
                     "visitor_id": visitor.id})

    return {"visit_id": visit.id, "pass_code": pass_obj.pass_code,
            "checked_in_at": now, "status": visit.status}


def _resolve_visit(visit: Visit | None, pass_code: str | None) -> Visit:
    if visit is not None:
        return visit
    pass_obj = find_pass(pass_code or "")
    if pass_obj is None:
        raise NotFoundError("Pass not found.", code="pass_not_found")
    return Visit.objects.get(pk=pass_obj.visit_id)


def check_out(*, visit: Visit | None = None, pass_code: str | None = None,
              machine_id: str = "", actor=None,
              self_service: bool = False) -> Visit:
    target = _resolve_visit(visit, pass_code)

    # BR-006 + BR-023: already closed -> conflict, and NO second log row.
    if target.status in ("COMPLETED", "TERMINATED", "INVALIDATED"):
        raise ConflictError(
            f"Visit is already {target.status}.",
            code="already_closed",
            details=[{"status": target.status}])

    if not self_service:                                       # BR-029
        policies.require_nominal_machine(policies.effective(), machine_id)

    now = timezone.now()
    actor_id = getattr(actor, "user_id", None)
    active = (Pass.objects
              .filter(visit_id=target.id, status="ACTIVE")
              .order_by("-id")
              .first())
    details: dict = {"self_service": self_service}
    if active is not None and not pass_is_live(active, now):
        if active.pass_type == "WALK_IN" and not target.extension_granted:
            # BR-018: one final extension for a walk-in whose pass ran out.
            target.extension_granted = True
            details["extension_granted"] = True
        else:
            # BR-003: an expired pass leaving is still a violation record.
            raise_violation(kind="EXPIRED_PASS", visit_id=target.id,
                            visitor_id=target.visitor_id,
                            pass_id=active.id,
                            details={"at": "check-out"})

    target.status = "COMPLETED"
    target.checked_out_at = now
    target.checked_out_by_user_id = actor_id
    target.save(update_fields=["status", "checked_out_at",
                               "checked_out_by_user_id",
                               "extension_granted", "updated_at"])

    _log(visit_id=target.id, visitor_id=target.visitor_id,
         event_type="CHECK_OUT", pass_id=active.id if active else None,
         machine_id=machine_id, recorded_by_user_id=actor_id,
         details=details, occurred_at=now)
    cleanup_stay_logs(target, ended_at=now)                   # BR-019
    close_on_visibility(target.id, actor_user_id=actor_id)    # BR-010

    visitor = Visitor.objects.get(pk=target.visitor_id)
    notifications.notify_visitor(
        visitor, kind="CHECK_OUT", subject="Visit ended",
        payload={"visit_id": target.id})
    request = _host_request(target)
    if request is not None:
        notifications.notify_host(
            request, kind="CHECK_OUT", subject="Visitor departed",
            payload={"visit_id": target.id})
    return target


def cleanup_stay_logs(visit: Visit, *, ended_at=None) -> int:
    """VMS-BR-019: every open STAY_START is closed when the visit ends."""
    ended_at = ended_at or timezone.now()
    starts = VisitLog.objects.filter(visit_id=visit.id,
                                     event_type="STAY_START")
    closed = 0
    for start in starts:
        ended = VisitLog.objects.filter(visit_id=visit.id,
                                        event_type="STAY_END",
                                        details={"for_log_id": start.id}
                                        ).exists()
        if ended:
            continue
        VisitLog.objects.create(
            visit_id=visit.id, visitor_id=visit.visitor_id,
            event_type="STAY_END", pass_id=start.pass_id,
            occurred_at=ended_at, recorded_by_user_id=None,
            details={"for_log_id": start.id})
        closed += 1
    return closed


def close_out_gate(*, gate_code: str, actor=None) -> dict:
    """VMS-BR-030: a gate may only close out once everyone is out."""
    on_site = Visit.objects.filter(status="ON_SITE")
    if gate_code:
        on_site = on_site.filter(gate_code=gate_code)
    remaining = list(on_site.values_list("id", flat=True))
    if remaining:
        raise ConflictError(
            f"{len(remaining)} visitor(s) are still on site.",
            code="visitors_still_on_site",
            details=[{"visit_ids": remaining[:50],
                      "count": len(remaining)}])
    return {"closed": True, "gate_code": gate_code,
            "closed_at": timezone.now(),
            "closed_by_user_id": getattr(actor, "user_id", None)}


def record_offline_entry(*, pass_code: str, gate_code: str,
                         machine_id: str, actor=None,
                         occurred_at=None) -> VisitLog:
    """VMS-CFR-025: a gate entry cached while connectivity is down."""
    pass_obj = find_pass(pass_code)
    if pass_obj is None:
        raise NotFoundError("Pass not found.", code="pass_not_found")
    return _log(visit_id=pass_obj.visit_id, visitor_id=pass_obj.visitor_id,
                event_type="OFFLINE_ENTRY", pass_id=pass_obj.id,
                gate_code=gate_code, machine_id=machine_id,
                recorded_by_user_id=getattr(actor, "user_id", None),
                occurred_at=occurred_at or timezone.now(),
                offline_cached=True)


def sync_offline_entries() -> int:
    """Reconcile cached entries once connectivity returns."""
    now = timezone.now()
    stale = list(VisitLog.objects.filter(offline_cached=True,
                                         synced_at__isnull=True))
    for row in stale:
        row.synced_at = now
        row.save(update_fields=["synced_at", "updated_at"])
    return len(stale)


def auto_checkout_expired(*, now=None) -> list[int]:
    """VMS-CFR-023: visits whose pass lapsed are completed automatically."""
    now = now or timezone.now()
    done: list[int] = []
    candidates = list(Visit.objects.filter(status="ON_SITE"))
    for visit in candidates:
        active = (Pass.objects
                  .filter(visit_id=visit.id, status="ACTIVE",
                          valid_until__lt=now)
                  .first())
        if active is None:
            continue
        check_out(visit=visit, actor=None, self_service=True)
        VisitLog.objects.filter(visit_id=visit.id,
                                event_type="CHECK_OUT").update(
            details={"auto_checkout": True})
        done.append(visit.id)
    return done
