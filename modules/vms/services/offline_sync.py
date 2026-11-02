"""Offline gate continuity: upload events captured while the link was down.

# VMS-CFR-025 · VMS-UC-028/039 · BW-VMS-11 · decision D-10
Each event carries a client UUID, so a replayed batch is idempotent. Events are
applied in `occurred_at` order and judged against the pass and policy as they
stood at `occurred_at`. The visitor is already through the gate, so a failure
never rejects the event: it is stored with `conflict=True` and an Alert.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, NotFoundError
from modules.vms.models import Alert, Gate, OfflineSyncRun, VisitLog, Zone
from modules.vms.selectors import gate as gate_sel
from modules.vms.services import gate as gate_svc
from modules.vms.services import policy, zone_access
from modules.vms.services.common import audit, authz

E = VisitLog.Event
MAX_BATCH = 500
APPLIED, CONFLICT, DUPLICATE, UNKNOWN = "applied", "conflict", "duplicate", "unknown_credential"


def _apply_one(*, actor, gate, event: dict, now) -> dict:
    cid = event["client_event_id"]
    occurred = event["occurred_at"]
    kind = event["event"]
    result = {"client_event_id": str(cid)}
    if VisitLog.objects.filter(client_event_id=cid).exists():
        return {**result, "status": DUPLICATE}
    credential = ({"qr_token": event["qr_token"]} if event.get("qr_token")
                  else {"otp": event.get("otp", "")})
    vp = gate_svc.locked_pass(credential=credential) if any(credential.values()) else None
    if vp is None:
        alert = zone_access.raise_alert(
            kind=Alert.Kind.GATE_FAILURE, severity=Alert.Severity.MEDIUM, ref_type="gate",
            ref_id=gate.pk, detail={"gate_id": gate.pk, "offline": True,
                                    "client_event_id": str(cid),
                                    "failures": [UNKNOWN],
                                    "occurred_at": occurred.isoformat()})
        return {**result, "status": UNKNOWN, "alert_id": alert.pk}
    zone_id = event.get("zone_id")
    if zone_id is not None and not Zone.objects.filter(pk=zone_id).exists():
        zone_id = None
    inside = gate_sel.open_check_in(vp.pk) is not None
    failures_codes: list[str] = []
    hit = None
    if kind == E.CHECK_IN:
        pol = policy.effective(at=occurred) if zone_id is not None else None
        ev = zone_access.evaluate(vp, now=occurred, zone_id=zone_id, open_checkin=inside,
                                  pol=pol)
        failures_codes, hit = ev.codes, ev.hit
    elif not inside:
        failures_codes = ["no_open_check_in"]
    conflict = bool(failures_codes)
    log = VisitLog.objects.create(
        visit_pass=vp, event=kind, zone_id=zone_id or gate.zone_id, gate=gate,
        device_id=event.get("device_id", gate.device_id)[:80], entry_point=gate.name,
        reason=",".join(failures_codes)[:255], logged_by_user_id=actor.user_id,
        offline=True, client_event_id=cid, occurred_at=occurred, synced_at=now,
        conflict=conflict)
    result.update(status=CONFLICT if conflict else APPLIED, visit_log_id=log.pk,
                  failures=failures_codes)
    if conflict:
        alert = zone_access.raise_alert(
            kind=Alert.Kind.BLACKLIST_HIT if hit else Alert.Kind.GATE_FAILURE,
            severity=hit.severity if hit else Alert.Severity.MEDIUM,
            ref_type="visitlog", ref_id=log.pk,
            detail={"gate_id": gate.pk, "pass_id": vp.pk, "offline": True,
                    "failures": failures_codes, "occurred_at": occurred.isoformat(),
                    "client_event_id": str(cid)})
        result["alert_id"] = alert.pk
        zone_access.notify_staff(
            gate_id=gate.pk, topic="gate.denied", key=f"gate-denied:{log.pk}",
            subject="Offline gate entry conflicts with current rules",
            body=f"An offline {kind} at {gate.name} failed: {', '.join(failures_codes)}.")
    return result


def sync(*, security_actor, gate_id: int, events: list[dict]) -> dict:
    """Apply a batch. Returns ``{"run_id", "total", "applied", "conflicted", "results"}``.

    Each event: client_event_id (UUID), event (check_in|check_out), occurred_at,
    qr_token or otp, optional zone_id and device_id.
    """
    if len(events) > MAX_BATCH:
        raise BadRequestError(f"At most {MAX_BATCH} events per batch.", code="batch_too_large")
    gate = Gate.objects.filter(pk=gate_id).first()
    if gate is None:
        raise NotFoundError("Gate not found.")
    now = timezone.now()
    authz.require_role(security_actor, "security", gate_id=gate.pk, at=now)
    ordered = sorted(events, key=lambda e: e["occurred_at"])
    results = []
    for event in ordered:
        try:
            with transaction.atomic():
                results.append(_apply_one(actor=security_actor, gate=gate, event=event,
                                          now=now))
        except IntegrityError:
            # A concurrent upload of the same client_event_id won the unique index.
            results.append({"client_event_id": str(event["client_event_id"]),
                            "status": DUPLICATE})
    applied = sum(r["status"] == APPLIED for r in results)
    conflicted = sum(r["status"] in (CONFLICT, UNKNOWN) for r in results)
    run = OfflineSyncRun.objects.create(
        gate=gate, events_total=len(results), events_applied=applied,
        events_conflicted=conflicted,
        detail={"results": results})
    audit.record(actor=security_actor, action="vms.gate.offline_synced", entity=run,
                 detail={"gate_id": gate.pk, "total": len(results), "applied": applied,
                         "conflicted": conflicted})
    return {"run_id": run.pk, "total": len(results), "applied": applied,
            "conflicted": conflicted, "duplicates": sum(r["status"] == DUPLICATE
                                                        for r in results),
            "results": results}


def cached_roster(*, security_actor, gate_id: int) -> list[dict]:
    """Passes the gate device may cache (no PII beyond initials)."""
    gate = Gate.objects.filter(pk=gate_id).first()
    if gate is None:
        raise NotFoundError("Gate not found.")
    authz.require_role(security_actor, "security", gate_id=gate.pk)
    return gate_sel.cached_roster(gate.pk)
