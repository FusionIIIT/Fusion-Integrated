"""Read side of the gate: open check-ins, denials, alerts, roster, elevations.

# VMS-CFR-013, 014, 025, 026
"""
from __future__ import annotations

import hashlib

from django.db.models import Exists, OuterRef, Q
from django.utils import timezone

from modules.vms.models import (
    Alert,
    Escalation,
    Gate,
    GateOverride,
    RoleAssignment,
    VisitLog,
    VisitPass,
    ZoneElevation,
)

E = VisitLog.Event
#: Events that change whether the visitor is inside.
_PRESENCE = (E.CHECK_IN, E.CHECK_OUT, E.AUTO_CHECK_OUT)


def open_check_in(pass_id: int) -> VisitLog | None:
    """The check-in log when the visitor is currently inside, else None.

    Lane D's check-out uses this: "inside" means the latest presence event
    for the pass is a check-in.
    """
    last = (VisitLog.objects.filter(visit_pass_id=pass_id, event__in=_PRESENCE)
            .order_by("-id").first())
    return last if last is not None and last.event == E.CHECK_IN else None


def alert_recipients(gate_id: int | None, at=None) -> list[int]:
    """User ids holding an active admin role, or a security role covering the gate."""
    at = at or timezone.now()
    scope = Q(scope_type=RoleAssignment.ScopeType.CAMPUS)
    if gate_id is not None:
        zone_id = Gate.objects.filter(pk=gate_id).values_list("zone_id", flat=True).first()
        scope |= Q(scope_type=RoleAssignment.ScopeType.GATE, scope_id=gate_id)
        if zone_id is not None:
            scope |= Q(scope_type=RoleAssignment.ScopeType.ZONE, scope_id=zone_id)
    qs = RoleAssignment.objects.filter(
        revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at).filter(
        Q(role=RoleAssignment.Role.ADMIN) | (Q(role=RoleAssignment.Role.SECURITY) & scope))
    return sorted(set(qs.values_list("user_id", flat=True)))


def gate_scope(user_id: int, at=None):
    """Gates this user may see: None means every gate, else a set of gate ids."""
    at = at or timezone.now()
    rows = list(RoleAssignment.objects.filter(
        user_id=user_id, revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at)
        .values_list("scope_type", "scope_id"))
    if not rows:
        return set()
    if any(t == RoleAssignment.ScopeType.CAMPUS for t, _ in rows):
        return None
    gates = {i for t, i in rows if t == RoleAssignment.ScopeType.GATE}
    zones = {i for t, i in rows if t == RoleAssignment.ScopeType.ZONE}
    if zones:
        gates |= set(Gate.objects.filter(zone_id__in=zones).values_list("pk", flat=True))
    return gates


def denials(user_id: int, status: str = "open"):
    """Denial logs in the caller's scope. status: open | overridden | escalated | all."""
    qs = (VisitLog.objects.filter(event=E.DENIED)
          .select_related("visit_pass__visit_request__visitor", "gate")
          .annotate(is_overridden=Exists(GateOverride.objects.filter(visit_log=OuterRef("pk"))),
                    is_escalated=Exists(Escalation.objects.filter(visit_log=OuterRef("pk")))))
    scope = gate_scope(user_id)
    if scope is not None:
        qs = qs.filter(gate_id__in=scope)
    if status == "open":
        qs = qs.filter(is_overridden=False)
    elif status == "overridden":
        qs = qs.filter(is_overridden=True)
    elif status == "escalated":
        qs = qs.filter(is_escalated=True)
    return qs.order_by("-id")


def alerts(user_id: int, status: str | None = None, kind: str | None = None):
    qs = Alert.objects.all()
    scope = gate_scope(user_id)
    if scope is not None:
        qs = qs.filter(detail__gate_id__in=sorted(scope))
    if status:
        qs = qs.filter(status=status)
    if kind:
        qs = qs.filter(kind=kind)
    return qs.order_by("-id")


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def cached_roster(gate_id: int, at=None) -> list[dict]:
    """Passes a gate device may cache for offline use (CFR-025).

    No PII beyond initials: credentials are sent as SHA-256 digests, which the
    device compares against the digest of what it scans or types.
    """
    at = at or timezone.now()
    passes = (VisitPass.objects.filter(
        is_active=True, terminated_at__isnull=True, valid_until__gt=at,
        visit_request__status="approved")
        .select_related("visit_request__visitor").prefetch_related("allowed_zones")
        .order_by("valid_until", "id"))
    rows = []
    for vp in passes:
        initials = "".join(w[0].upper() for w in vp.visit_request.visitor.full_name.split()[:3])
        rows.append({
            "pass_id": vp.pk, "initials": initials, "pass_type": vp.pass_type,
            "valid_from": vp.valid_from, "valid_until": vp.valid_until,
            "qr_sha256": _digest(vp.qr_token), "otp_sha256": _digest(vp.otp),
            "zone_ids": sorted(z.pk for z in vp.allowed_zones.all())})
    return rows


def elevations(*, pass_id=None, active_only=False, at=None):
    qs = ZoneElevation.objects.select_related("zone")
    if pass_id:
        qs = qs.filter(visit_pass_id=pass_id)
    if active_only:
        at = at or timezone.now()
        qs = qs.filter(revoked_at__isnull=True, starts_at__lte=at, ends_at__gt=at)
    return qs.order_by("-id")
