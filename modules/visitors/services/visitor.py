"""All writes to a visit request (CW-VMS-01 … CW-VMS-07).

Raises domain errors rather than DRF exceptions, so the same call works from a
management command or a Celery task.

Ref: 03_VMS_Use_Case_Specifications_v1.3, 05_VMS_Workflow_Specifications_v1.3
"""
from __future__ import annotations

import logging
import uuid
from datetime import date, datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.visitors.domain import rules
from modules.visitors.models import (
    AccessPolicy,
    BlacklistEntry,
    EmergencyMuster,
    GateLog,
    MusterRollCall,
    PreAuthorization,
    SafeListEntry,
    TemporaryZoneElevation,
    VIPPermission,
    VisitApproval,
    VisitRequest,
    ZoneAccessLog,
    ZoneDefinition,
)

log = logging.getLogger("fusion.visitors")

OPEN_STATUSES = ("pending_host", "pending_admin")
ACTIVE_STATUSES = ("approved", "pass_active", "on_site")


def _published_policy() -> AccessPolicy | None:
    return AccessPolicy.objects.filter(is_published=True).first()


def _blacklist_numbers() -> set[str]:
    return set(
        BlacklistEntry.objects
        .filter(is_active=True, entry_type="blacklist")
        .values_list("id_document_number", flat=True)
    )


def _safe_listed(bl_entry_id: int, now: datetime) -> bool:
    return SafeListEntry.objects.filter(
        blacklist_entry_id=bl_entry_id,
        valid_from__lte=now, valid_until__gte=now,
    ).exists()


def _generate_pass_code() -> str:
    return f"VMS-{uuid.uuid4().hex[:12].upper()}"


def _as_rule_error(exc: rules.RuleViolation) -> ConflictError:
    return ConflictError(f"{exc.message} ({exc.rule})", code="rule_violation")


def _check_duplicate(visitor_id_number: str, host_user_id: int,
                     expected_date: date, exclude_id: int | None = None) -> None:
    """BR-VMS-038: no duplicate pending/active visit for same visitor+host+date."""
    qs = VisitRequest.objects.filter(
        visitor_id_number=visitor_id_number,
        host_user_id=host_user_id,
        expected_date=expected_date,
        status__in=(*OPEN_STATUSES, *ACTIVE_STATUSES),
    ).exclude(pk=exclude_id)
    if qs.exists():
        raise ConflictError(
            "A visit request already exists for this visitor, host, and date.",
            code="duplicate_visit",
        )


# --- VMS-UC-010: Pre-register visit (BW-VMS-01) -----------------------------

@transaction.atomic
def pre_register_visit(actor, *, visitor_name: str, visitor_phone: str,
                       visitor_email: str = "", visitor_organization: str = "",
                       visitor_id_type: str, visitor_id_number: str,
                       host_user_id: int, purpose: str,
                       expected_date: date,
                       expected_time_from=None, expected_time_until=None,
                       number_of_visitors: int = 1,
                       ) -> VisitRequest:
    data = {
        "visitor_name": visitor_name, "visitor_phone": visitor_phone,
        "visitor_id_type": visitor_id_type, "visitor_id_number": visitor_id_number,
        "host_user_id": host_user_id, "purpose": purpose,
        "expected_date": expected_date,
    }
    try:
        rules.validate_pre_registration(data)
        rules.validate_id_document(visitor_id_type, visitor_id_number)
        rules.check_advance_window(expected_date, timezone.localdate())
        rules.check_visiting_hours(expected_time_from)
        rules.check_max_duration(expected_time_from, expected_time_until)
        rules.check_not_blacklisted(visitor_id_number, _blacklist_numbers())
    except rules.RuleViolation as exc:
        raise _as_rule_error(exc) from exc

    _check_duplicate(visitor_id_number, host_user_id, expected_date)

    policy = _published_policy()
    pre_auth = _match_pre_authorization(host_user_id, visitor_id_number,
                                        expected_date)
    vip = _match_vip(visitor_id_number)

    if vip:
        initial_status = "pass_active"
        pass_type = "VIP"
    elif pre_auth:
        initial_status = "pass_active"
        pass_type = "PRE_AUTHORIZED"
    else:
        initial_status = "pending_host"
        pass_type = "PRE_REGISTERED"

    visit = VisitRequest.objects.create(
        kind="standard",
        status=initial_status,
        visitor_name=visitor_name,
        visitor_email=visitor_email,
        visitor_phone=visitor_phone,
        visitor_organization=visitor_organization,
        visitor_id_type=visitor_id_type,
        visitor_id_number=visitor_id_number,
        host_user_id=host_user_id,
        purpose=purpose,
        expected_date=expected_date,
        expected_time_from=expected_time_from,
        expected_time_until=expected_time_until,
        number_of_visitors=number_of_visitors,
        pass_type=pass_type,
        pass_code=_generate_pass_code() if initial_status == "pass_active" else None,
        pass_valid_from=timezone.now() if initial_status == "pass_active" else None,
        pass_valid_until=_compute_pass_expiry(expected_date, expected_time_until,
                                              policy)
        if initial_status == "pass_active" else None,
        pre_authorization=pre_auth,
        vip_permission=vip,
        registered_by=actor.user_id if actor else None,
    )
    log.info("visit pre-registered", extra={"visit_id": visit.pk,
                                            "status": initial_status})
    return visit


def _match_pre_authorization(host_user_id: int, visitor_id_number: str,
                             visit_date: date) -> PreAuthorization | None:
    """BR-VMS-195: check for active pre-authorization."""
    return (PreAuthorization.objects
            .filter(user_id=host_user_id, visitor_id_number=visitor_id_number,
                    is_active=True, valid_from__lte=visit_date,
                    valid_until__gte=visit_date)
            .first())


def _match_vip(visitor_id_number: str) -> VIPPermission | None:
    """BR-VMS-196: check for active VIP permission."""
    now = timezone.now()
    return (VIPPermission.objects
            .filter(visitor_id_number=visitor_id_number, is_active=True,
                    valid_from__lte=now, valid_until__gte=now)
            .first())


def _compute_pass_expiry(expected_date: date, expected_time_until=None,
                         policy: AccessPolicy | None = None) -> datetime | None:
    if expected_time_until:
        return timezone.make_aware(
            datetime.combine(expected_date, expected_time_until))
    max_hours = policy.max_visit_duration_hours if policy else rules.DEFAULT_MAX_VISIT_HOURS
    return timezone.make_aware(
        datetime.combine(expected_date, rules.DEFAULT_VISITING_HOURS[1]))


# --- VMS-UC-013: Decide visit request (BW-VMS-01, BW-VMS-02) ----------------

@transaction.atomic
def decide_visit(actor, visit_id: int, *, action: str,
                 note: str = "") -> VisitRequest:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit request not found.")
    if visit.status not in OPEN_STATUSES:
        raise ConflictError("This visit is no longer pending approval.",
                            code="not_pending")

    VisitApproval.objects.create(
        visit=visit, action=action,
        actor_user_id=actor.user_id,
        actor_role=getattr(actor, "active_role", "host"),
        note=note,
    )

    if action == "approve":
        visit.status = "pass_active"
        visit.pass_type = visit.pass_type or "PRE_REGISTERED"
        visit.pass_code = _generate_pass_code()
        visit.pass_valid_from = timezone.now()
        visit.pass_valid_until = _compute_pass_expiry(
            visit.expected_date, visit.expected_time_until, _published_policy())
        visit.decided_by = actor.user_id
        visit.decided_at = timezone.now()
        visit.decision_note = note
        log.info("visit approved", extra={"visit_id": visit.pk})
    elif action == "reject":
        visit.status = "rejected"
        visit.decided_by = actor.user_id
        visit.decided_at = timezone.now()
        visit.decision_note = note
        log.info("visit rejected", extra={"visit_id": visit.pk})
    else:
        raise BadRequestError(f"Invalid action: {action}")

    visit.save()
    return visit


# --- VMS-UC-017: Register walk-in visitor (BW-VMS-06/07) --------------------

@transaction.atomic
def register_walkin(actor, *, visitor_name: str, visitor_phone: str,
                    visitor_id_type: str, visitor_id_number: str,
                    host_user_id: int, purpose: str,
                    gate_name: str = "",
                    ) -> VisitRequest:
    try:
        rules.validate_id_document(visitor_id_type, visitor_id_number)
        rules.check_not_blacklisted(visitor_id_number, _blacklist_numbers())
    except rules.RuleViolation as exc:
        raise _as_rule_error(exc) from exc

    today = timezone.localdate()
    _check_duplicate(visitor_id_number, host_user_id, today)

    policy = _published_policy()
    now = timezone.now()
    duration = (policy.default_walkin_duration_minutes
                if policy else rules.DEFAULT_WALKIN_MINUTES)

    visit = VisitRequest.objects.create(
        kind="walkin",
        status="pending_host",
        visitor_name=visitor_name,
        visitor_phone=visitor_phone,
        visitor_id_type=visitor_id_type,
        visitor_id_number=visitor_id_number,
        host_user_id=host_user_id,
        purpose=purpose,
        expected_date=today,
        pass_type="WALK_IN",
        registered_by=actor.user_id,
    )

    GateLog.objects.create(
        visit=visit, event_type="check_in", gate_name=gate_name or "main",
        recorded_by=actor.user_id, note="Walk-in registration",
    )
    log.info("walk-in registered", extra={"visit_id": visit.pk})
    return visit


# --- VMS-UC-018: Validate visitor pass at gate (BW-VMS-01, CW-VMS-03) -------

@transaction.atomic
def validate_pass_at_gate(actor, visit_id: int, *,
                          gate_name: str) -> GateLog:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")

    now = timezone.now()
    if not rules.pass_is_valid(visit.pass_valid_from, visit.pass_valid_until, now):
        gl = GateLog.objects.create(
            visit=visit, event_type="denied", gate_name=gate_name,
            recorded_by=actor.user_id, note="Pass not valid at this time.",
        )
        log.warning("gate denied — invalid pass", extra={"visit_id": visit.pk})
        return gl

    try:
        rules.check_not_blacklisted(visit.visitor_id_number, _blacklist_numbers())
    except rules.RuleViolation:
        gl = GateLog.objects.create(
            visit=visit, event_type="denied", gate_name=gate_name,
            recorded_by=actor.user_id, note="Blacklist match at gate.",
        )
        return gl

    visit.status = "on_site"
    visit.checked_in_at = now
    visit.checked_in_by = actor.user_id
    visit.save()

    gl = GateLog.objects.create(
        visit=visit, event_type="check_in", gate_name=gate_name,
        recorded_by=actor.user_id,
    )
    log.info("gate check-in", extra={"visit_id": visit.pk})
    return gl


# --- VMS-UC-021: Check out visitor at gate (BR-VMS-105) ----------------------

@transaction.atomic
def checkout_visitor(actor, visit_id: int, *, gate_name: str) -> VisitRequest:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")
    if visit.status != "on_site":
        raise ConflictError("Visitor is not currently on site.",
                            code="not_on_site")

    now = timezone.now()
    visit.status = "completed"
    visit.checked_out_at = now
    visit.checked_out_by = actor.user_id
    visit.save()

    GateLog.objects.create(
        visit=visit, event_type="check_out", gate_name=gate_name,
        recorded_by=actor.user_id,
    )
    log.info("visitor checked out", extra={"visit_id": visit.pk})
    return visit


# --- VMS-UC-016 / VMS-UC-036: Terminate visit early (BR-VMS-073) ------------

@transaction.atomic
def terminate_visit(actor, visit_id: int, *, reason: str = "") -> VisitRequest:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")
    actor_role = getattr(actor, "active_role", "host")
    if not rules.can_terminate(visit.status, actor_role):
        raise ConflictError("This visit cannot be terminated in its current state.",
                            code="cannot_terminate")

    visit.status = "terminated"
    visit.decided_by = actor.user_id
    visit.decided_at = timezone.now()
    visit.decision_note = reason
    visit.save()

    VisitApproval.objects.create(
        visit=visit, action="terminate",
        actor_user_id=actor.user_id, actor_role=actor_role,
        note=reason,
    )
    log.info("visit terminated early", extra={"visit_id": visit.pk})
    return visit


# --- VMS-UC-019: Process manual gate override (BR-VMS-085) ------------------

@transaction.atomic
def manual_gate_override(actor, visit_id: int, *, gate_name: str,
                         reason: str) -> GateLog:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")

    visit.status = "on_site"
    visit.checked_in_at = timezone.now()
    visit.checked_in_by = actor.user_id
    visit.save()

    gl = GateLog.objects.create(
        visit=visit, event_type="override", gate_name=gate_name,
        recorded_by=actor.user_id, note=f"Manual override: {reason}",
    )
    log.info("manual gate override", extra={"visit_id": visit.pk})
    return gl


# --- VMS-UC-023: Validate zone access (CW-VMS-04, BR-VMS-191) ---------------

@transaction.atomic
def validate_zone_access(actor, visit_id: int, *,
                         zone_code: str) -> ZoneAccessLog:
    visit = VisitRequest.objects.filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")
    zone = ZoneDefinition.objects.filter(code=zone_code, is_active=True).first()
    if zone is None:
        raise NotFoundError("Zone not found.")

    allowed = visit.allowed_zones or []
    now = timezone.now()
    has_elevation = TemporaryZoneElevation.objects.filter(
        visit=visit, zone=zone, used=False, valid_until__gte=now).exists()

    if zone.access_level != "general" and zone_code not in allowed and not has_elevation:
        entry = ZoneAccessLog.objects.create(
            visit=visit, zone=zone, action="denied",
            recorded_by=actor.user_id, note="Unauthorized zone access attempt.",
        )
        log.warning("zone access denied", extra={"visit_id": visit.pk,
                                                  "zone": zone_code})
        return entry

    if has_elevation:
        elev = TemporaryZoneElevation.objects.filter(
            visit=visit, zone=zone, used=False, valid_until__gte=now).first()
        if elev:
            elev.used = True
            elev.used_at = now
            elev.save()

    entry = ZoneAccessLog.objects.create(
        visit=visit, zone=zone, action="entry",
        recorded_by=actor.user_id,
    )
    log.info("zone access granted", extra={"visit_id": visit.pk,
                                            "zone": zone_code})
    return entry


# --- VMS-UC-024: Grant temporary zone elevation (BR-VMS-096) ----------------

@transaction.atomic
def grant_zone_elevation(actor, visit_id: int, *, zone_code: str,
                         valid_minutes: int = 60) -> TemporaryZoneElevation:
    visit = VisitRequest.objects.filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")
    zone = ZoneDefinition.objects.filter(code=zone_code, is_active=True).first()
    if zone is None:
        raise NotFoundError("Zone not found.")

    elev = TemporaryZoneElevation.objects.create(
        visit=visit, zone=zone, granted_by=actor.user_id,
        valid_until=timezone.now() + timezone.timedelta(minutes=valid_minutes),
    )
    log.info("zone elevation granted", extra={"visit_id": visit.pk,
                                               "zone": zone_code})
    return elev


# --- VMS-UC-026/032: Trigger emergency muster (BR-VMS-130) ------------------

@transaction.atomic
def trigger_muster(actor, *, reason: str) -> EmergencyMuster:
    on_site = VisitRequest.objects.filter(status="on_site")
    muster = EmergencyMuster.objects.create(
        triggered_by=actor.user_id,
        trigger_role=getattr(actor, "active_role", "admin"),
        reason=reason,
        total_on_site=on_site.count(),
    )
    for visit in on_site:
        MusterRollCall.objects.create(muster=muster, visit=visit)
    log.info("emergency muster triggered", extra={"muster_id": muster.pk})
    return muster


# --- VMS-UC-027: Perform emergency roll-call ---------------------------------

@transaction.atomic
def account_visitor_in_muster(actor, muster_id: int, visit_id: int, *,
                              location_note: str = "") -> MusterRollCall:
    rc = (MusterRollCall.objects
          .filter(muster_id=muster_id, visit_id=visit_id)
          .first())
    if rc is None:
        raise NotFoundError("Roll-call entry not found.")
    rc.accounted = True
    rc.accounted_by = actor.user_id
    rc.accounted_at = timezone.now()
    rc.location_note = location_note
    rc.save()

    muster = rc.muster
    muster.total_accounted = (MusterRollCall.objects
                              .filter(muster=muster, accounted=True).count())
    muster.save(update_fields=["total_accounted"])
    return rc


# --- VMS-UC-037: Expire pending visit requests (event-triggered) -------------

def expire_pending_requests() -> int:
    now = timezone.now()
    policy = _published_policy()
    timeout = (policy.approval_timeout_hours
               if policy else rules.DEFAULT_APPROVAL_TIMEOUT_HOURS)

    expired = []
    for visit in VisitRequest.objects.filter(status__in=OPEN_STATUSES):
        if rules.is_approval_timed_out(visit.created_at, now, timeout):
            expired.append(visit.pk)

    count = VisitRequest.objects.filter(pk__in=expired).update(status="expired")
    if count:
        log.info("expired %d pending visit requests", count)
    return count


# --- VMS-UC-038: Automatically check out visits (event-triggered) ------------

def auto_checkout_expired() -> int:
    now = timezone.now()
    visits = VisitRequest.objects.filter(status="on_site")
    checked_out = []
    for visit in visits:
        if rules.should_auto_checkout(visit.pass_valid_until, now):
            checked_out.append(visit.pk)

    count = VisitRequest.objects.filter(pk__in=checked_out).update(
        status="completed", checked_out_at=now)
    if count:
        log.info("auto-checked-out %d visits", count)
    return count


# --- VMS-UC-034: Decide visit extension (BW-VMS-23) -------------------------

@transaction.atomic
def request_extension(actor, visit_id: int, *,
                      extended_until_time=None,
                      reason: str = "") -> VisitRequest:
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit not found.")
    if visit.status not in ("on_site", "pass_active"):
        raise ConflictError("Only active visits can be extended.",
                            code="not_active")

    ext = VisitRequest.objects.create(
        kind="extension", parent=visit, status="pending_admin",
        visitor_name=visit.visitor_name,
        visitor_phone=visit.visitor_phone,
        visitor_email=visit.visitor_email,
        visitor_id_type=visit.visitor_id_type,
        visitor_id_number=visit.visitor_id_number,
        host_user_id=visit.host_user_id,
        purpose=f"Extension: {reason}",
        expected_date=visit.expected_date,
        expected_time_until=extended_until_time,
        pass_type=visit.pass_type,
        registered_by=actor.user_id,
    )
    log.info("extension requested", extra={"visit_id": visit.pk,
                                            "ext_id": ext.pk})
    return ext
