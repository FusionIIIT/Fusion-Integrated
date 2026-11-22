from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.domain.validation import zones_allowed
from modules.vms.models import (
    EmergencyMuster,
    MusterRollCall,
    VisitLog,
    VisitRequest,
    ZoneAccessEvent,
    ZoneAlert,
    ZoneElevation,
)


@transaction.atomic
def record_zone_access(*, visit_id, zone, actor_id, allowed, reason_code="", metadata=None):
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id).first()
    if visit is None:
        raise NotFoundError("Visit request not found.")
    now = timezone.now()
    elevated = ZoneElevation.objects.filter(
        request=visit, zone=zone, valid_from__lte=now, valid_until__gt=now, revoked_at__isnull=True
    ).exists()
    permitted = zones_allowed([zone], visit.approved_zones) or elevated
    grant = bool(allowed and permitted and visit.status == "on_site")
    event = ZoneAccessEvent.objects.create(
        request=visit,
        zone=zone[:80],
        decision="granted" if grant else "denied",
        reason_code=reason_code[:40] or ("zone_not_permitted" if not permitted else "not_on_site"),
        occurred_at=now,
        recorded_by_user_id=actor_id,
        metadata=metadata or {},
    )
    VisitLog.objects.create(
        request=visit,
        event_type="zone_granted" if grant else "zone_denied",
        occurred_at=now,
        zone=zone[:80],
        recorded_by_user_id=actor_id,
        reason=event.reason_code,
        metadata=metadata or {},
    )
    if not grant:
        ZoneAlert.objects.create(access_event=event)
    return event


@transaction.atomic
def elevate_zone(*, visit_id, zone, actor_id, reason, minutes):
    if minutes < 1 or minutes > 240:
        raise ConflictError(
            "Zone elevation must be between 1 and 240 minutes.", code="invalid_zone_window"
        )
    visit = VisitRequest.objects.select_for_update().filter(pk=visit_id, status="on_site").first()
    if visit is None:
        raise NotFoundError("On-site visit not found.")
    now = timezone.now()
    elevation = ZoneElevation.objects.create(
        request=visit,
        zone=zone[:80],
        valid_from=now,
        valid_until=min(visit.ends_at, now + timedelta(minutes=minutes)),
        reason=reason[:500],
        granted_by_user_id=actor_id,
    )
    if elevation.valid_until <= now:
        raise ConflictError(
            "Visit ends before the elevation could take effect.", code="invalid_zone_window"
        )
    return elevation


@transaction.atomic
def trigger_muster(*, actor_id, location="", instructions=""):
    active = EmergencyMuster.objects.select_for_update().filter(status="active").first()
    if active:
        raise ConflictError("An emergency muster is already active.", code="muster_already_active")
    now = timezone.now()
    on_site = list(VisitRequest.objects.filter(status="on_site").values_list("id", flat=True))
    try:
        with transaction.atomic():
            muster = EmergencyMuster.objects.create(
                triggered_by_user_id=actor_id,
                triggered_at=now,
                location=location[:160],
                instructions=instructions[:500],
                roster_created_at=now,
                roster_count=len(on_site),
            )
    except IntegrityError as exc:
        raise ConflictError(
            "An emergency muster is already active.", code="muster_already_active"
        ) from exc
    MusterRollCall.objects.bulk_create(
        [MusterRollCall(muster=muster, request_id=visit_id) for visit_id in on_site], batch_size=500
    )
    return muster


@transaction.atomic
def record_roll_call(*, muster_id, visit_id, actor_id, status, note=""):
    muster = (
        EmergencyMuster.objects.select_for_update().filter(pk=muster_id, status="active").first()
    )
    if muster is None:
        raise NotFoundError("Active muster not found.")
    roll = (
        MusterRollCall.objects.select_for_update()
        .filter(muster=muster, request_id=visit_id)
        .first()
    )
    if roll is None:
        raise NotFoundError("Visitor is not in this muster roster.")
    if status not in {"accounted", "last_seen", "unaccounted"}:
        raise ConflictError("Unsupported roll-call state.", code="invalid_roll_call_state")
    roll.status = status
    roll.note = note[:300]
    roll.updated_by_user_id = actor_id
    roll.save(update_fields=["status", "note", "updated_by_user_id", "updated_at"])
    return roll


@transaction.atomic
def complete_muster(*, muster_id, actor_id):
    muster = (
        EmergencyMuster.objects.select_for_update().filter(pk=muster_id, status="active").first()
    )
    if muster is None:
        raise NotFoundError("Active muster not found.")
    rows = list(MusterRollCall.objects.filter(muster=muster).values_list("status", flat=True))
    muster.status = "completed"
    muster.completed_at = timezone.now()
    muster.completed_by_user_id = actor_id
    muster.report = {key: rows.count(key) for key in ("accounted", "last_seen", "unaccounted")}
    muster.save(
        update_fields=["status", "completed_at", "completed_by_user_id", "report", "updated_at"]
    )
    return muster


@transaction.atomic
def handle_zone_alert(*, alert_id, actor_id, note, status="handled"):
    alert = ZoneAlert.objects.select_for_update().filter(pk=alert_id, status="open").first()
    if alert is None:
        raise NotFoundError("Open zone alert not found.")
    if status not in {"handled", "false_positive"}:
        raise ConflictError("Unsupported alert resolution.", code="invalid_alert_status")
    alert.status = status
    alert.handling_note = note[:500]
    alert.handled_by_user_id = actor_id
    alert.handled_at = timezone.now()
    alert.save(
        update_fields=["status", "handling_note", "handled_by_user_id", "handled_at", "updated_at"]
    )
    return alert
