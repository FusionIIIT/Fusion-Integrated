from django.db import transaction
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError
from modules.vms.models import (
    AuditEvent,
    EventGuestBatch,
    EventGuestBatchRow,
    EventRecord,
    IntegrationSetting,
    VipPermission,
    VisitorProfile,
    VisitPass,
    VisitRequest,
)

_SENSITIVE_CONFIG_KEYS = {"secret", "password", "token", "api_key", "private_key"}


def _safe_config(config):
    if not isinstance(config, dict) or len(config) > 40:
        raise ConflictError(
            "Integration config must be a small object of non-secret settings.",
            code="invalid_integration_config",
        )
    if any(
        any(secret in str(key).casefold() for secret in _SENSITIVE_CONFIG_KEYS) for key in config
    ):
        raise ConflictError(
            "Store integration credentials in the platform secret store.", code="secret_in_config"
        )
    return config


@transaction.atomic
def update_integration(*, integration_type, endpoint, enabled, config, actor_id):
    if integration_type not in dict(IntegrationSetting.TYPE):
        raise ConflictError("Unsupported integration type.", code="invalid_integration_type")
    setting, _ = IntegrationSetting.objects.select_for_update().get_or_create(
        integration_type=integration_type
    )
    setting.endpoint = endpoint
    setting.enabled = enabled
    setting.available = False  # Availability is verified by the owning connector.
    setting.config = _safe_config(config)
    setting.updated_by_user_id = actor_id
    setting.save(
        update_fields=[
            "endpoint",
            "enabled",
            "available",
            "config",
            "updated_by_user_id",
            "updated_at",
        ]
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="super_admin",
        action="integration.configure",
        object_type="IntegrationSetting",
        object_id=str(setting.pk),
        after={"integration_type": integration_type, "endpoint": endpoint, "enabled": enabled},
    )
    return setting


@transaction.atomic
def grant_vip_permission(*, visitor_id, zones, valid_from, valid_until, actor_id, reason):
    visitor = VisitorProfile.objects.filter(pk=visitor_id, is_active=True).first()
    if visitor is None:
        raise NotFoundError("Visitor profile not found.")
    if valid_from <= timezone.now() or valid_until <= valid_from:
        raise ConflictError(
            "VIP permission requires a future, ordered validity window.", code="invalid_vip_window"
        )
    permission = VipPermission.objects.create(
        visitor=visitor,
        zones=list(zones),
        valid_from=valid_from,
        valid_until=valid_until,
        granted_by_user_id=actor_id,
        reason=reason[:500],
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="super_admin",
        action="vip_permission.grant",
        object_type="VipPermission",
        object_id=str(permission.pk),
        after={
            "visitor_id": visitor.pk,
            "zones": list(zones),
            "valid_until": valid_until.isoformat(),
        },
    )
    return permission


@transaction.atomic
def revoke_vip_permission(*, permission_id, actor_id, reason):
    permission = (
        VipPermission.objects.select_for_update()
        .filter(pk=permission_id, revoked_at__isnull=True)
        .first()
    )
    if permission is None:
        raise NotFoundError("Active VIP permission not found.")
    permission.revoked_at = timezone.now()
    permission.revoked_by_user_id = actor_id
    permission.save(update_fields=["revoked_at", "revoked_by_user_id", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="super_admin",
        action="vip_permission.revoke",
        object_type="VipPermission",
        object_id=str(permission.pk),
        reason=reason[:500],
        after={"visitor_id": permission.visitor_id},
    )
    return permission


@transaction.atomic
def create_event(
    *,
    name,
    external_event_id,
    starts_at,
    ends_at,
    zones,
    fast_lane_enabled,
    overflow_limit,
    rate_limit_per_minute,
    actor_id,
):
    now = timezone.now()
    if starts_at <= now or ends_at <= starts_at:
        raise ConflictError(
            "Event window must be in the future and ordered.", code="invalid_event_window"
        )
    if overflow_limit is not None and overflow_limit < 1:
        raise ConflictError("Overflow limit must be positive.", code="invalid_event_limit")
    if rate_limit_per_minute is not None and rate_limit_per_minute < 1:
        raise ConflictError("Rate limit must be positive.", code="invalid_event_limit")
    event = EventRecord.objects.create(
        name=name.strip(),
        external_event_id=external_event_id,
        starts_at=starts_at,
        ends_at=ends_at,
        zones=list(zones),
        fast_lane_enabled=fast_lane_enabled,
        overflow_limit=overflow_limit,
        rate_limit_per_minute=rate_limit_per_minute,
        created_by_user_id=actor_id,
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action="event.create",
        object_type="EventRecord",
        object_id=str(event.pk),
        after={
            "name": event.name,
            "starts_at": starts_at.isoformat(),
            "ends_at": ends_at.isoformat(),
        },
    )
    return event


@transaction.atomic
def update_event_controls(
    *, event_id, actor_id, fast_lane_enabled, overflow_limit, rate_limit_per_minute
):
    event = EventRecord.objects.select_for_update().filter(pk=event_id).first()
    if event is None:
        raise NotFoundError("Event not found.")
    if event.status == "completed":
        raise ConflictError("Completed event controls are immutable.", code="event_completed")
    for value in (overflow_limit, rate_limit_per_minute):
        if value is not None and value < 1:
            raise ConflictError("Event limits must be positive.", code="invalid_event_limit")
    event.fast_lane_enabled = fast_lane_enabled
    event.overflow_limit = overflow_limit
    event.rate_limit_per_minute = rate_limit_per_minute
    event.save(
        update_fields=["fast_lane_enabled", "overflow_limit", "rate_limit_per_minute", "updated_at"]
    )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action="event.controls_update",
        object_type="EventRecord",
        object_id=str(event.pk),
        after={
            "fast_lane_enabled": event.fast_lane_enabled,
            "overflow_limit": event.overflow_limit,
            "rate_limit_per_minute": event.rate_limit_per_minute,
        },
    )
    return event


@transaction.atomic
def transition_event(*, event_id, actor_id, action):
    event = EventRecord.objects.select_for_update().filter(pk=event_id).first()
    if event is None:
        raise NotFoundError("Event not found.")
    if action == "activate" and event.status == "draft" and event.ends_at > timezone.now():
        event.status = "active"
    elif action == "complete" and event.status == "active" and event.ends_at <= timezone.now():
        event.status = "completed"
    else:
        raise ConflictError(
            "Event cannot perform this lifecycle transition.", code="invalid_event_transition"
        )
    event.save(update_fields=["status", "updated_at"])
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action=f"event.{action}",
        object_type="EventRecord",
        object_id=str(event.pk),
        after={"status": event.status},
    )
    return event


@transaction.atomic
def import_event_guests(*, event_id, visit_ids, actor_id, idempotency_key):
    event = EventRecord.objects.filter(pk=event_id).first()
    if event is None:
        raise NotFoundError("Event not found.")
    if not idempotency_key or len(idempotency_key) > 100:
        raise ConflictError("A valid idempotency key is required.", code="invalid_event_import")
    if (
        not isinstance(visit_ids, (list, tuple))
        or not visit_ids
        or len(visit_ids) > 500
        or any(
            not isinstance(value, int) or isinstance(value, bool) or value < 1
            for value in visit_ids
        )
        or len(set(visit_ids)) != len(visit_ids)
    ):
        raise ConflictError(
            "Supply between 1 and 500 unique visit IDs.", code="invalid_event_import"
        )
    batch, created = EventGuestBatch.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={"event": event, "created_by_user_id": actor_id, "row_count": len(visit_ids)},
    )
    if not created:
        if batch.event_id != event.pk:
            raise ConflictError(
                "Idempotency key belongs to another event.", code="idempotency_conflict"
            )
        return batch
    for visit_id in visit_ids:
        status, reason, linked = "rejected", "Visit is not eligible for event entry.", None
        try:
            with transaction.atomic():
                visit_pass = (
                    VisitPass.objects.select_for_update().filter(request_id=visit_id).first()
                )
                visit = (
                    VisitRequest.objects.select_for_update()
                    .select_related("visitor")
                    .filter(pk=visit_id)
                    .first()
                )
                current_event = EventRecord.objects.select_for_update().filter(pk=event_id).first()
                if visit is None:
                    reason = "Visit request not found."
                elif current_event is None or current_event.status == "completed":
                    reason = "Event is not accepting guest-list updates."
                elif visit.status != "approved" or visit_pass is None:
                    reason = "Visit must already be approved and have a pass."
                elif visit.event_id not in (None, event.pk):
                    reason = "Visit is assigned to another event."
                elif visit.event_id == event.pk:
                    reason = "Visit is already assigned to this event."
                elif (
                    visit.starts_at < current_event.starts_at
                    or visit.ends_at > current_event.ends_at
                ):
                    reason = "Visit validity must fit inside the event window."
                elif not visit.identity_documents.filter(scan_status="clean").exists():
                    reason = "Identity document has not passed security scanning."
                elif not set(visit.approved_zones).issubset(set(current_event.zones)):
                    reason = "Visit zones exceed the event zones."
                else:
                    visit.event = current_event
                    visit.kind = "event"
                    visit.save(update_fields=["event", "kind", "updated_at"])
                    status, reason, linked = "accepted", "", visit
        except (VisitRequest.DoesNotExist, VisitPass.DoesNotExist):
            reason = "Approved visit pass is unavailable."
        EventGuestBatchRow.objects.create(
            batch=batch, request=linked, submitted_visit_id=visit_id, status=status, reason=reason
        )
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind="admin",
        action="event.guest_import",
        object_type="EventGuestBatch",
        object_id=str(batch.pk),
        after={
            "event_id": event.pk,
            "accepted": batch.rows.filter(status="accepted").count(),
            "rejected": batch.rows.filter(status="rejected").count(),
        },
    )
    return batch
