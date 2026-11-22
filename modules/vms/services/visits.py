import hashlib
import hmac
import uuid
from datetime import timedelta

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.db.models import Max, Q
from django.utils import timezone

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.directory import contracts as directory
from modules.vms.domain.state_machine import PENDING_URGENT, resolve
from modules.vms.domain.validation import RuleViolation, validate_visit_window
from modules.vms.models import (
    AccessPolicyVersion,
    AuditEvent,
    BlacklistEntry,
    EventRecord,
    GateAttempt,
    NotificationOutbox,
    PreAuthorization,
    RegistryVersion,
    VipPermission,
    VisitLog,
    VisitorAccessCredential,
    VisitorDocument,
    VisitorProfile,
    VisitPass,
    VisitRequest,
    VisitTransition,
)


def _fingerprint(value: str) -> str:
    secret = getattr(settings, "VMS_ID_FINGERPRINT_KEY", None) or settings.SECRET_KEY
    return hmac.new(secret.encode(), value.strip().encode(), hashlib.sha256).hexdigest()


def _audit(actor_id, actor_kind, action, obj, *, reason="", after=None, request_id=""):
    AuditEvent.objects.create(
        actor_user_id=actor_id,
        actor_kind=actor_kind,
        action=action,
        object_type=obj.__class__.__name__,
        object_id=str(obj.pk),
        request_id=request_id,
        reason=reason,
        after=after or {},
    )


def _queue_host_arrival(visit):
    NotificationOutbox.objects.get_or_create(
        dedupe_key=f"visit:{visit.pk}:host-arrival",
        defaults={
            "topic": "visit.checked_in",
            "recipient_user_id": visit.host_user_id,
            "subject": "Visitor has arrived",
            "body": f"Visitor check-in was recorded for visit request {visit.pk}.",
            "payload": {"visit_id": visit.pk},
        },
    )


def _policy(now):
    policy = (
        AccessPolicyVersion.objects.filter(
            status="published",
            effective_from__lte=now,
        )
        .filter(effective_until__isnull=True)
        .order_by("-version")
        .first()
    )
    if policy:
        return policy
    # Safe baseline keeps a fresh installation usable; administrators can publish
    # a new immutable version. This is never silently selected over a published row.
    next_version = (
        AccessPolicyVersion.objects.filter(scope_key="campus").aggregate(value=Max("version"))[
            "value"
        ]
        or 0
    ) + 1
    return AccessPolicyVersion.objects.get_or_create(
        scope_key="campus",
        version=next_version,
        defaults={
            "status": "published",
            "effective_from": now,
            "published_at": now,
            "maximum_visit_minutes": 480,
            "walk_in_minutes": 240,
            "approval_timeout_minutes": 1440,
            "contingency_timeout_minutes": 60,
            "reminder_minutes": [720, 1200],
        },
    )[0]


def _active_blacklist(name, fingerprint, now):
    registry = RegistryVersion.objects.filter(status="published", effective_from__lte=now)
    version = registry.order_by("-version").first()
    if version is None:
        return False
    normalized = " ".join(name.casefold().split())
    return (
        BlacklistEntry.objects.filter(version=version, is_active=True)
        .filter(
            Q(expires_at__isnull=True) | Q(expires_at__gt=now),
        )
        .filter(Q(normalized_name=normalized) | Q(identity_fingerprint=fingerprint))
        .exists()
    )


def _record_gate_attempt(
    *,
    request=None,
    token_fingerprint="",
    checkpoint="",
    result="denied",
    failure_code="",
    actor_id=None,
    idempotency_key="",
    at=None,
):
    values = {
        "request": request,
        "presented_fingerprint": token_fingerprint[:64],
        "checkpoint": checkpoint[:100],
        "result": result,
        "failure_code": failure_code[:40],
        "actor_user_id": actor_id,
        "attempted_at": at or timezone.now(),
        "idempotency_key": idempotency_key[:100],
    }
    if idempotency_key:
        return GateAttempt.objects.get_or_create(idempotency_key=idempotency_key, defaults=values)[
            0
        ]
    return GateAttempt.objects.create(**values)


def _event_entry_failure(event, now):
    if event.status != "active" or now < event.starts_at or now >= event.ends_at:
        return "event_inactive", "The event is not accepting entries."
    if (
        event.overflow_limit is not None
        and VisitRequest.objects.filter(event=event, status="on_site").count()
        >= event.overflow_limit
    ):
        return "event_overflow", "The event occupancy limit has been reached."
    if (
        event.rate_limit_per_minute is not None
        and VisitLog.objects.filter(
            request__event=event, event_type="entry", occurred_at__gt=now - timedelta(minutes=1)
        ).count()
        >= event.rate_limit_per_minute
    ):
        return "event_rate_limit", "The event entry rate limit has been reached."
    return "", ""


@transaction.atomic
def register_visit(
    *,
    name,
    email,
    phone,
    id_type,
    id_value,
    purpose,
    host_user_id,
    starts_at,
    ends_at,
    requested_zones=(),
    request_id="",
    document_info=None,
):
    if not document_info:
        raise ConflictError("An identity document is required.", code="identity_document_required")
    now = timezone.now()
    identity_hash = _fingerprint(id_type.casefold() + ":" + id_value.strip())
    host = directory.get_users([host_user_id]).get(host_user_id)
    if host is None or host.kind not in {"faculty", "staff"}:
        raise NotFoundError("Selected host is unavailable.")
    if _active_blacklist(name, identity_hash, now):
        raise PermissionDeniedError("This request cannot be submitted. Contact campus security.")
    policy = _policy(now)
    urgent = starts_at - now < timedelta(minutes=policy.advance_registration_minutes)
    try:
        validate_visit_window(
            starts_at=starts_at,
            ends_at=ends_at,
            now=now,
            maximum=timedelta(minutes=policy.maximum_visit_minutes),
            advance_window=timedelta(0),
        )
    except RuleViolation as exc:
        raise ConflictError(str(exc), code=exc.code) from exc
    if policy.visiting_hours_start and policy.visiting_hours_end:
        start_time, end_time = (
            starts_at.timetz().replace(tzinfo=None),
            ends_at.timetz().replace(tzinfo=None),
        )
        start_bound, end_bound = policy.visiting_hours_start, policy.visiting_hours_end
        inside = (
            start_bound <= start_time and end_time <= end_bound
            if start_bound <= end_bound
            else start_time >= start_bound or end_time <= end_bound
        )
        if not inside:
            raise ConflictError(
                "Visit falls outside the published visiting hours.", code="outside_visiting_hours"
            )
    visitor, _ = VisitorProfile.objects.get_or_create(
        email=email.casefold(),
        id_fingerprint=identity_hash,
        defaults={
            "display_name": name.strip(),
            "phone": phone,
            "id_type": id_type,
            "id_last_four": id_value[-4:],
        },
    )
    visitor = VisitorProfile.objects.select_for_update().get(pk=visitor.pk)
    if not visitor.is_active:
        raise PermissionDeniedError("Visitor access is disabled.")
    if VisitRequest.objects.filter(
        visitor=visitor,
        host_user_id=host_user_id,
        starts_at__lt=ends_at,
        ends_at__gt=starts_at,
        status__in=[
            "pending",
            "pending_admin_contingency",
            "pending_urgent_review",
            "approved",
            "on_site",
        ],
    ).exists():
        raise ConflictError("A matching visit request already exists.", code="duplicate_visit")
    visit = VisitRequest.objects.create(
        visitor=visitor,
        host_user_id=host_user_id,
        purpose=purpose.strip(),
        starts_at=starts_at,
        ends_at=ends_at,
        requested_zones=list(requested_zones),
        submitted_at=now,
        approval_due_at=now + timedelta(minutes=policy.approval_timeout_minutes),
        policy_version=policy,
    )
    VisitorDocument.objects.create(
        request=visit,
        visitor=visitor,
        document_type=id_type,
        storage_key=document_info["storage_key"],
        filename=document_info["filename"],
        content_type=document_info["content_type"],
        size_bytes=document_info["size_bytes"],
        sha256=document_info["sha256"],
    )
    transition = resolve("not_submitted", "submit", "visitor")
    VisitTransition.objects.create(
        request=visit,
        from_status=transition.source,
        to_status=transition.target,
        event=transition.event,
        actor_kind="visitor",
    )
    if urgent:
        follow_up = resolve(visit.status, "urgent_review", "system")
        visit.status = PENDING_URGENT
        visit.save(update_fields=["status", "updated_at"])
        VisitTransition.objects.create(
            request=visit,
            from_status=follow_up.source,
            to_status=follow_up.target,
            event=follow_up.event,
            actor_kind="system",
        )
        _audit(None, "system", "visit.urgent_review", visit, after={"status": visit.status})
    preauthorization = (
        PreAuthorization.objects.filter(
            host_user_id=host_user_id,
            visitor=visitor,
            revoked_at__isnull=True,
            valid_from__lte=starts_at,
            valid_until__gte=ends_at,
        )
        .order_by("-valid_until")
        .first()
    )
    if (
        preauthorization
        and not urgent
        and set(requested_zones).issubset(set(preauthorization.zones))
        and not set(requested_zones).intersection(set(policy.restricted_zones))
    ):
        prior = visit.status
        visit.status = "approved"
        visit.approved_zones = list(requested_zones)
        visit.decided_by_user_id = host_user_id
        visit.decided_at = now
        visit.decision_reason = "Host pre-authorization"
        visit.save(
            update_fields=[
                "status",
                "approved_zones",
                "decided_by_user_id",
                "decided_at",
                "decision_reason",
                "updated_at",
            ]
        )
        VisitTransition.objects.create(
            request=visit,
            from_status=prior,
            to_status="approved",
            event="approve",
            actor_user_id=host_user_id,
            actor_kind="host",
            reason="Host pre-authorization",
        )
        nonce = uuid.uuid4()
        VisitPass.objects.create(
            request=visit,
            pass_type=visit.kind,
            credential_nonce=nonce,
            valid_from=visit.starts_at,
            valid_until=visit.ends_at,
            permitted_zones=visit.approved_zones,
        )
        NotificationOutbox.objects.create(
            topic="visit.approved",
            dedupe_key=f"visit:{visit.pk}:approved",
            recipient_email=visitor.email,
            subject="Your visit is approved",
            body=(
                f"Your visit request {visit.pk} was approved. "
                "The gate pass credential is included below."
            ),
            payload={"visit_id": visit.pk},
        )
    credential = VisitorAccessCredential.objects.create(
        visitor=visitor, nonce=uuid.uuid4(), expires_at=now + timedelta(days=90)
    )
    if visit.status == "pending":
        NotificationOutbox.objects.create(
            topic="visit.host_approval",
            dedupe_key=f"visit:{visit.pk}:submitted",
            recipient_user_id=host_user_id,
            subject="Visitor request requires your decision",
            body=f"A visitor request (reference {visit.pk}) is waiting for your decision.",
            payload={"visit_id": visit.pk},
        )
    # Address and access link are retained only in the delivery outbox; delivery
    # clears sensitive content after successful send.
    NotificationOutbox.objects.create(
        topic="visit.visitor_access",
        dedupe_key=f"visitor:{visitor.pk}:credential:{credential.pk}",
        recipient_email=visitor.email,
        subject="Your visitor access link",
        body="Access your visitor requests using the secure credential in this message.",
        payload={"credential_id": credential.pk},
    )
    _audit(
        None,
        "visitor",
        "visit.submit",
        visit,
        request_id=request_id,
        after={"host_user_id": host_user_id, "status": visit.status},
    )
    return visit


def authenticate_visitor(token: str):
    try:
        data = signing.loads(token, salt="vms.visitor-access", max_age=60 * 60 * 24 * 90)
        nonce = uuid.UUID(data["credential"])
        credential = VisitorAccessCredential.objects.select_related("visitor").get(nonce=nonce)
    except (
        ValueError,
        KeyError,
        TypeError,
        signing.BadSignature,
        VisitorAccessCredential.DoesNotExist,
    ) as exc:
        raise NotFoundError("Visitor access link is invalid or expired.") from exc
    now = timezone.now()
    if credential.revoked_at or credential.expires_at <= now or not credential.visitor.is_active:
        raise NotFoundError("Visitor access link is invalid or expired.")
    VisitorAccessCredential.objects.filter(pk=credential.pk).update(last_used_at=now)
    return credential.visitor


@transaction.atomic
def decide_visit(
    *,
    visit_id,
    actor_id,
    actor_kind,
    decision,
    reason="",
    zones=None,
    instructions="",
    starts_at=None,
    ends_at=None,
):
    visit = (
        VisitRequest.objects.select_for_update()
        .select_related("visitor")
        .filter(pk=visit_id)
        .first()
    )
    if visit is None:
        raise NotFoundError("Visit request not found.")
    if actor_kind == "host" and visit.host_user_id != actor_id:
        raise NotFoundError("Visit request not found.")
    event = "approve" if decision == "approve" else "reject"
    if actor_kind == "admin" and visit.kind == "walk_in":
        event = "approve_contingency" if decision == "approve" else "reject_contingency"
    elif actor_kind == "admin" and visit.status == PENDING_URGENT:
        event = "approve_urgent" if decision == "approve" else "reject_urgent"
    try:
        transition = resolve(visit.status, event, actor_kind)
    except ValueError as exc:
        raise ConflictError(str(exc), code="invalid_visit_transition") from exc
    prior = visit.status
    if decision == "approve" and starts_at is not None and ends_at is not None:
        policy = visit.policy_version or _policy(timezone.now())
        try:
            validate_visit_window(
                starts_at=starts_at,
                ends_at=ends_at,
                now=timezone.now(),
                maximum=timedelta(minutes=policy.maximum_visit_minutes),
                advance_window=timedelta(0),
            )
        except RuleViolation as exc:
            raise ConflictError(str(exc), code=exc.code) from exc
        visit.starts_at, visit.ends_at = starts_at, ends_at
    if decision == "approve" and visit.kind == "walk_in" and transition.target == "approved":
        visit.starts_at = timezone.now()
        duration = visit.policy_version.walk_in_minutes if visit.policy_version_id else 240
        visit.ends_at = visit.starts_at + timedelta(minutes=duration)
    visit.status = transition.target
    visit.decided_by_user_id = actor_id
    visit.decided_at = timezone.now()
    visit.decision_reason = reason[:500]
    if decision == "approve" and transition.target == "approved":
        vip_permissions = list(
            VipPermission.objects.filter(
                visitor=visit.visitor,
                revoked_at__isnull=True,
                valid_from__lte=visit.starts_at,
                valid_until__gte=visit.ends_at,
            )
        )
        vip_zones = {zone for permission in vip_permissions for zone in permission.zones}
        selected_zones = list(zones if zones is not None else visit.requested_zones)
        if not set(selected_zones).issubset(set(visit.requested_zones) | vip_zones):
            raise ConflictError(
                "Approved zones must be within the requested zones.", code="zone_scope_exceeded"
            )
        restricted = set(visit.policy_version.restricted_zones if visit.policy_version else [])
        if set(selected_zones) & restricted:
            raise ConflictError(
                "A requested zone is restricted by the active policy.", code="restricted_zone"
            )
        visit.approved_zones = sorted(set(selected_zones) | vip_zones)
        visit.special_instructions = instructions[:500]
    changed_fields = [
        "status",
        "decided_by_user_id",
        "decided_at",
        "decision_reason",
        "approved_zones",
        "special_instructions",
        "updated_at",
    ]
    if (
        decision == "approve"
        and transition.target == "approved"
        and (visit.kind == "walk_in" or starts_at is not None)
    ):
        changed_fields.extend(["starts_at", "ends_at"])
    visit.save(update_fields=changed_fields)
    VisitTransition.objects.create(
        request=visit,
        from_status=prior,
        to_status=visit.status,
        event=event,
        actor_user_id=actor_id,
        actor_kind=actor_kind,
        reason=reason[:500],
    )
    activated = visit.status == "approved"
    if decision == "approve" and activated:
        nonce = uuid.uuid4()
        VisitPass.objects.update_or_create(
            request=visit,
            defaults={
                "pass_type": "vip" if vip_permissions else visit.kind,
                "credential_nonce": nonce,
                "valid_from": visit.starts_at,
                "valid_until": visit.ends_at,
                "permitted_zones": visit.approved_zones,
                "status": "active",
            },
        )
        NotificationOutbox.objects.create(
            topic="visit.approved",
            dedupe_key=f"visit:{visit.pk}:approved",
            recipient_email=visit.visitor.email,
            subject="Your visit is approved",
            body=(
                f"Your visit request {visit.pk} was approved. "
                "The gate pass credential is included below."
            ),
            payload={"visit_id": visit.pk},
        )
    elif decision == "reject":
        NotificationOutbox.objects.create(
            topic="visit.rejected",
            dedupe_key=f"visit:{visit.pk}:rejected",
            recipient_email=visit.visitor.email,
            subject="Visit request update",
            body=f"Your visit request {visit.pk} was declined. Contact the host for details.",
            payload={"visit_id": visit.pk},
        )
    elif decision == "approve":
        NotificationOutbox.objects.create(
            topic="visit.host_decision",
            dedupe_key=f"visit:{visit.pk}:admin-approved-urgent",
            recipient_user_id=visit.host_user_id,
            subject="Urgent visit request needs your decision",
            body=f"Urgent visit request {visit.pk} passed Admin review and awaits your decision.",
            payload={"visit_id": visit.pk},
        )
    _audit(
        actor_id,
        actor_kind,
        f"visit.{decision}",
        visit,
        reason=reason,
        after={"status": visit.status},
    )
    return visit


@transaction.atomic
def terminate_visit(*, visit_id, actor_id, actor_kind, reason):
    if not reason or not reason.strip():
        raise ConflictError("A termination reason is required.", code="termination_reason_required")
    visit = (
        VisitRequest.objects.select_for_update()
        .select_related("visitor")
        .filter(pk=visit_id)
        .first()
    )
    if visit is None or (actor_kind == "host" and visit.host_user_id != actor_id):
        raise NotFoundError("Active visit not found.")
    try:
        transition = resolve(visit.status, "terminate", actor_kind)
    except ValueError as exc:
        raise ConflictError(str(exc), code="invalid_visit_transition") from exc
    prior = visit.status
    now = timezone.now()
    visit.status = transition.target
    visit.decided_by_user_id = actor_id
    visit.decided_at = now
    visit.decision_reason = reason.strip()[:500]
    visit.save(
        update_fields=[
            "status",
            "decided_by_user_id",
            "decided_at",
            "decision_reason",
            "updated_at",
        ]
    )
    VisitTransition.objects.create(
        request=visit,
        from_status=prior,
        to_status=visit.status,
        event="terminate",
        actor_user_id=actor_id,
        actor_kind=actor_kind,
        reason=visit.decision_reason,
    )
    VisitPass.objects.filter(request=visit, status="active").update(
        status="revoked",
        revoked_at=now,
        revoked_by_user_id=actor_id,
        revocation_reason=visit.decision_reason,
        updated_at=now,
    )
    _audit(
        actor_id,
        actor_kind,
        "visit.terminate",
        visit,
        reason=visit.decision_reason,
        after={"status": visit.status, "was_on_site": prior == "on_site"},
    )
    NotificationOutbox.objects.get_or_create(
        dedupe_key=f"visit:{visit.pk}:terminated:{visit.updated_at.isoformat()}",
        defaults={
            "topic": "visit.terminated",
            "recipient_email": visit.visitor.email,
            "subject": "Your campus visit authorization was terminated",
            "body": f"Visit request {visit.pk} was terminated. Contact your host for details.",
        },
    )
    return visit


@transaction.atomic
def decide_visit_extension(*, visit_id, actor_id, decision, ends_at, reason):
    if not reason or not reason.strip():
        raise ConflictError(
            "An extension decision reason is required.", code="extension_reason_required"
        )
    visit = (
        VisitRequest.objects.select_for_update()
        .select_related("visitor")
        .filter(pk=visit_id)
        .first()
    )
    if visit is None or visit.status not in {"approved", "on_site"}:
        raise NotFoundError("Active visit not found.")
    visit_pass = (
        VisitPass.objects.select_for_update().filter(request=visit, status="active").first()
    )
    if visit_pass is None:
        raise ConflictError("Active pass not found.", code="pass_not_active")
    now = timezone.now()
    if decision == "approve":
        if ends_at <= visit.ends_at or ends_at <= now:
            raise ConflictError(
                "An extension must end after the current visit and now.",
                code="invalid_extension_window",
            )
        policy = visit.policy_version or _policy(now)
        if ends_at - visit.starts_at <= timedelta(minutes=policy.maximum_visit_minutes):
            raise ConflictError(
                "The extension decision path is only for visits beyond the policy maximum.",
                code="extension_not_required",
            )
        prior_end = visit.ends_at
        visit.ends_at = ends_at
        visit.save(update_fields=["ends_at", "updated_at"])
        visit_pass.valid_until = ends_at
        visit_pass.save(update_fields=["valid_until", "updated_at"])
        VisitTransition.objects.create(
            request=visit,
            from_status=visit.status,
            to_status=visit.status,
            event="extension_approve",
            actor_user_id=actor_id,
            actor_kind="admin",
            reason=reason.strip()[:500],
        )
        _audit(
            actor_id,
            "admin",
            "visit.extension_approve",
            visit,
            reason=reason,
            after={"prior_ends_at": prior_end.isoformat(), "ends_at": ends_at.isoformat()},
        )
    elif decision == "reject":
        _audit(
            actor_id,
            "admin",
            "visit.extension_reject",
            visit,
            reason=reason,
            after={"requested_ends_at": ends_at.isoformat()},
        )
    else:
        raise ConflictError("Unsupported extension decision.", code="invalid_extension_decision")
    NotificationOutbox.objects.get_or_create(
        dedupe_key=f"visit:{visit.pk}:extension-{decision}:{ends_at.isoformat()}",
        defaults={
            "topic": f"visit.extension_{decision}",
            "recipient_email": visit.visitor.email,
            "subject": "Your visit extension was "
            + ("approved" if decision == "approve" else "rejected"),
            "body": (
                f"Visit request {visit.pk} was {decision}d. "
                + (f"New end time: {ends_at.isoformat()}." if decision == "approve" else "")
            ),
            "payload": {"visit_id": visit.pk},
        },
    )
    return visit


@transaction.atomic
def record_manual_visit_log(
    *,
    visit_id,
    actor_id,
    event_type,
    occurred_at,
    location="",
    zone="",
    reason="",
    metadata=None,
    gate_attempt_id=None,
):
    visit_pass = None
    if event_type == "entry":
        visit_pass = VisitPass.objects.select_for_update().filter(request_id=visit_id).first()
    visit = (
        VisitRequest.objects.select_for_update()
        .select_related("visitor")
        .filter(pk=visit_id)
        .first()
    )
    if visit is None:
        raise NotFoundError("Visit request not found.")
    allowed = {"entry", "exit", "zone_granted", "zone_denied", "gate_denied"}
    if event_type not in allowed:
        raise ConflictError("Unsupported manual visit-log event.", code="invalid_visit_log_type")
    if event_type == "entry":
        if visit.status != "approved":
            raise ConflictError(
                "Manual entry requires an approved visit.", code="invalid_visit_state"
            )
        now = timezone.now()
        if occurred_at > now or occurred_at < visit.starts_at or occurred_at >= visit.ends_at:
            raise ConflictError(
                "Manual entry time must fall inside the visit validity window.",
                code="manual_entry_time_invalid",
            )
        override = (
            GateAttempt.objects.select_for_update()
            .filter(
                pk=gate_attempt_id,
                request=visit,
                result="overridden",
                failure_code="pass_not_valid",
            )
            .first()
            if gate_attempt_id
            else None
        )
        if not override and (
            visit_pass is None
            or visit_pass.status != "active"
            or visit_pass.valid_from > now
            or visit_pass.valid_until <= now
        ):
            raise ConflictError(
                "Manual entry requires an active pass or authorized override.",
                code="manual_entry_not_authorized",
            )
        if not visit.identity_documents.filter(scan_status="clean").exists():
            raise ConflictError(
                "Identity document has not passed security scanning.",
                code="identity_document_not_cleared",
            )
        if _active_blacklist(visit.visitor.display_name, visit.visitor.id_fingerprint, now):
            raise PermissionDeniedError("Pass is not valid for entry.")
        if visit.event_id:
            event = EventRecord.objects.select_for_update().filter(pk=visit.event_id).first()
            failure_code, message = (
                _event_entry_failure(event, now)
                if event
                else ("event_unavailable", "The event is not available for entry.")
            )
            if failure_code:
                raise ConflictError(message, code=failure_code)
        transition = resolve("approved", "check_in", "security")
        visit.status = transition.target
        visit.save(update_fields=["status", "updated_at"])
        VisitTransition.objects.create(
            request=visit,
            from_status=transition.source,
            to_status=transition.target,
            event="check_in",
            actor_user_id=actor_id,
            actor_kind="security",
            reason=reason[:500],
        )
        if visit_pass:
            visit_pass.status = "used"
            visit_pass.save(update_fields=["status", "updated_at"])
        _queue_host_arrival(visit)
    if event_type == "exit" and visit.status not in {"on_site", "terminated"}:
        raise ConflictError("Manual exit requires an on-site visit.", code="invalid_visit_state")
    log = VisitLog.objects.create(
        request=visit,
        event_type=event_type,
        occurred_at=occurred_at,
        location=location[:160],
        zone=zone[:80],
        recorded_by_user_id=actor_id,
        source="manual",
        reason=reason[:500],
        metadata=metadata or {},
    )
    _audit(
        actor_id,
        "security",
        "visit.manual_log",
        visit,
        reason=reason,
        after={"event_type": event_type, "log_id": log.pk},
    )
    return log


@transaction.atomic
def decide_gate_override(*, attempt_id, actor_id, decision, reason):
    if not reason or not reason.strip():
        raise ConflictError(
            "An override decision requires justification.", code="override_reason_required"
        )
    attempt = GateAttempt.objects.filter(
        pk=attempt_id, result="override_pending", overridden_at__isnull=True
    ).first()
    if attempt is None:
        raise NotFoundError("Blocked gate attempt not found.")
    now = timezone.now()
    if decision == "authorize":
        # The spec leaves override eligibility unresolved. Keep it narrow:
        # never override a blacklist, document, event-control, or unknown-token failure.
        if attempt.failure_code != "pass_not_valid" or attempt.request_id is None:
            raise ConflictError(
                "This gate failure is not eligible for manual override.",
                code="override_not_eligible",
            )
        visit_pass = (
            VisitPass.objects.select_for_update().filter(request_id=attempt.request_id).first()
        )
        visit = (
            VisitRequest.objects.select_for_update()
            .select_related("visitor")
            .filter(pk=attempt.request_id, status="approved")
            .first()
        )
        attempt = (
            GateAttempt.objects.select_for_update()
            .filter(pk=attempt_id, result="override_pending", overridden_at__isnull=True)
            .first()
        )
        if attempt is None:
            raise ConflictError(
                "Gate attempt was already decided.", code="override_already_decided"
            )
        if (
            visit is None
            or visit_pass is None
            or visit_pass.status != "revoked"
            or visit.starts_at > now
            or visit.ends_at <= now
            or not visit.identity_documents.filter(scan_status="clean").exists()
            or _active_blacklist(visit.visitor.display_name, visit.visitor.id_fingerprint, now)
        ):
            raise ConflictError(
                "The visit is not eligible for a manual override.", code="override_not_eligible"
            )
        attempt.result = "overridden"
    elif decision == "deny":
        attempt = (
            GateAttempt.objects.select_for_update()
            .filter(pk=attempt_id, result="override_pending", overridden_at__isnull=True)
            .first()
        )
        if attempt is None:
            raise ConflictError(
                "Gate attempt was already decided.", code="override_already_decided"
            )
        attempt.result = "denied"
    else:
        raise ConflictError("Unsupported gate override decision.", code="invalid_override_decision")
    attempt.override_reason = reason.strip()[:500]
    attempt.overridden_by_user_id = actor_id
    attempt.overridden_at = now
    attempt.updated_at = now
    attempt.save(
        update_fields=[
            "result",
            "override_reason",
            "overridden_by_user_id",
            "overridden_at",
            "updated_at",
        ]
    )
    _audit(
        actor_id,
        "admin",
        f"gate.override_{decision}",
        attempt,
        reason=attempt.override_reason,
        after={"failure_code": attempt.failure_code, "request_id": attempt.request_id},
    )
    return attempt


@transaction.atomic
def escalate_gate_attempt(*, attempt_id, actor_id, reason):
    if not reason or not reason.strip():
        raise ConflictError("An escalation reason is required.", code="escalation_reason_required")
    attempt = (
        GateAttempt.objects.select_for_update()
        .filter(pk=attempt_id, result="denied", overridden_at__isnull=True)
        .first()
    )
    if attempt is None:
        raise NotFoundError("Denied gate attempt not found.")
    attempt.result = "override_pending"
    attempt.override_reason = reason.strip()[:500]
    attempt.updated_at = timezone.now()
    attempt.save(update_fields=["result", "override_reason", "updated_at"])
    _audit(
        actor_id,
        "security",
        "gate.override_escalate",
        attempt,
        reason=reason,
        after={"failure_code": attempt.failure_code, "request_id": attempt.request_id},
    )
    return attempt


@transaction.atomic
def register_walk_in(
    *,
    name,
    email,
    phone,
    id_type,
    id_value,
    purpose,
    host_user_id,
    actor_id,
    host_unavailable=False,
    requested_zones=(),
    document_info=None,
):
    if not document_info:
        raise ConflictError("An identity document is required.", code="identity_document_required")
    now = timezone.now()
    policy = _policy(now)
    identity_hash = _fingerprint(id_type.casefold() + ":" + id_value.strip())
    if _active_blacklist(name, identity_hash, now):
        raise PermissionDeniedError("This request cannot be submitted. Contact campus security.")
    host = directory.get_users([host_user_id]).get(host_user_id)
    if host is None or host.kind not in {"faculty", "staff"}:
        raise NotFoundError("Selected host is unavailable.")
    visitor, _ = VisitorProfile.objects.get_or_create(
        email=email.casefold(),
        id_fingerprint=identity_hash,
        defaults={
            "display_name": name.strip(),
            "phone": phone,
            "id_type": id_type,
            "id_last_four": id_value[-4:],
        },
    )
    visitor = VisitorProfile.objects.select_for_update().get(pk=visitor.pk)
    if VisitRequest.objects.filter(
        visitor=visitor,
        host_user_id=host_user_id,
        status__in=[
            "pending",
            "pending_admin_contingency",
            "pending_urgent_review",
            "approved",
            "on_site",
        ],
        ends_at__gt=now,
    ).exists():
        raise ConflictError(
            "A matching active visit request already exists.", code="duplicate_visit"
        )
    end = now + timedelta(minutes=policy.walk_in_minutes)
    visit = VisitRequest.objects.create(
        visitor=visitor,
        host_user_id=host_user_id,
        kind="walk_in",
        status="pending",
        purpose=purpose.strip(),
        starts_at=now,
        ends_at=end,
        requested_zones=list(requested_zones),
        submitted_at=now,
        approval_due_at=now
        + timedelta(
            minutes=(
                policy.contingency_timeout_minutes
                if host_unavailable
                else policy.approval_timeout_minutes
            )
        ),
        policy_version=policy,
    )
    VisitorDocument.objects.create(
        request=visit,
        visitor=visitor,
        document_type=id_type,
        storage_key=document_info["storage_key"],
        filename=document_info["filename"],
        content_type=document_info["content_type"],
        size_bytes=document_info["size_bytes"],
        sha256=document_info["sha256"],
    )
    first = resolve("not_submitted", "submit_walk_in", "security")
    VisitTransition.objects.create(
        request=visit,
        from_status=first.source,
        to_status=first.target,
        event=first.event,
        actor_user_id=actor_id,
        actor_kind="security",
    )
    if host_unavailable:
        next_transition = resolve(visit.status, "require_admin", "system")
        visit.status = next_transition.target
        visit.save(update_fields=["status", "updated_at"])
        VisitTransition.objects.create(
            request=visit,
            from_status=next_transition.source,
            to_status=next_transition.target,
            event=next_transition.event,
            actor_kind="system",
            reason="Host unavailable for gate approval",
        )
        _audit(
            actor_id, "system", "visit.contingency_review", visit, after={"status": visit.status}
        )
    else:
        NotificationOutbox.objects.create(
            topic="visit.host_approval",
            dedupe_key=f"visit:{visit.pk}:submitted",
            recipient_user_id=host_user_id,
            subject="Walk-in visitor requests approval",
            body=f"Walk-in request {visit.pk} is waiting for your decision.",
            payload={"visit_id": visit.pk},
        )
    _audit(
        actor_id,
        "security",
        "visit.walk_in",
        visit,
        after={"status": visit.status, "host_user_id": host_user_id},
    )
    return visit


@transaction.atomic
def create_preauthorization(*, host_user_id, visitor_id, valid_from, valid_until, zones, reason=""):
    now = timezone.now()
    if valid_from <= now or valid_until <= valid_from:
        raise ConflictError(
            "Pre-authorization must have a future, ordered validity window.",
            code="invalid_preauthorization_window",
        )
    visitor = VisitorProfile.objects.filter(pk=visitor_id, is_active=True).first()
    if visitor is None:
        raise NotFoundError("Visitor profile not found.")
    policy = _policy(now)
    if set(zones) & set(policy.restricted_zones):
        raise ConflictError(
            "Pre-authorization includes a policy-restricted zone.", code="restricted_zone"
        )
    authorization = PreAuthorization.objects.create(
        host_user_id=host_user_id,
        visitor=visitor,
        zones=list(zones),
        valid_from=valid_from,
        valid_until=valid_until,
        created_by_user_id=host_user_id,
        reason=reason[:500],
    )
    _audit(
        host_user_id,
        "host",
        "preauthorization.create",
        authorization,
        after={"visitor_id": visitor.pk, "valid_until": valid_until.isoformat()},
    )
    return authorization


@transaction.atomic
def revoke_preauthorization(*, authorization_id, host_user_id):
    authorization = (
        PreAuthorization.objects.select_for_update()
        .filter(pk=authorization_id, host_user_id=host_user_id, revoked_at__isnull=True)
        .first()
    )
    if authorization is None:
        raise NotFoundError("Pre-authorization not found.")
    authorization.revoked_at = timezone.now()
    authorization.save(update_fields=["revoked_at", "updated_at"])
    _audit(
        host_user_id,
        "host",
        "preauthorization.revoke",
        authorization,
        after={"visitor_id": authorization.visitor_id},
    )
    return authorization


@transaction.atomic
def reconcile_offline_entries(*, limit=250):
    from modules.vms.models import OfflineGateEvent

    events = list(
        OfflineGateEvent.objects.filter(status="pending")
        .order_by("event_at", "pk")
        .values_list("pk", flat=True)[:limit]
    )
    reconciled = 0
    for event_id in events:
        with transaction.atomic():
            offline = (
                OfflineGateEvent.objects.select_for_update()
                .filter(pk=event_id, status="pending")
                .first()
            )
            if offline is None:
                continue
            visit_pass = (
                VisitPass.objects.select_for_update()
                .select_related("request")
                .filter(credential_nonce=offline.credential_nonce)
                .first()
            )
            now = timezone.now()
            if (
                visit_pass is None
                or visit_pass.valid_from > offline.event_at
                or visit_pass.valid_until < offline.event_at
            ):
                offline.status = "conflict"
                offline.reconciliation_note = "pass_invalid_at_event_time"
                offline.reconciled_at = now
                offline.save(
                    update_fields=["status", "reconciliation_note", "reconciled_at", "updated_at"]
                )
                continue
            visit = VisitRequest.objects.select_for_update().get(pk=visit_pass.request_id)
            if visit.status == "approved":
                visit.status = "on_site"
                visit.save(update_fields=["status", "updated_at"])
                VisitTransition.objects.create(
                    request=visit,
                    from_status="approved",
                    to_status="on_site",
                    event="check_in",
                    actor_user_id=offline.recorded_by_user_id,
                    actor_kind="security",
                    reason="Offline entry reconciled",
                )
                VisitLog.objects.create(
                    request=visit,
                    event_type="offline_entry",
                    occurred_at=offline.event_at,
                    location=offline.checkpoint,
                    recorded_by_user_id=offline.recorded_by_user_id,
                    source="offline",
                )
                _queue_host_arrival(visit)
                offline.status = "reconciled"
                offline.reconciliation_note = "entry_reconciled"
                reconciled += 1
            else:
                offline.status = "conflict"
                offline.reconciliation_note = f"visit_state_{visit.status}"
            offline.reconciled_at = now
            offline.save(
                update_fields=["status", "reconciliation_note", "reconciled_at", "updated_at"]
            )
    return reconciled


@transaction.atomic
def cache_offline_entry(*, token, checkpoint, event_at, actor_id, idempotency_key):
    from modules.vms.models import OfflineGateEvent

    try:
        data = signing.loads(token, salt="vms.visit-pass", max_age=60 * 60 * 24 * 120)
        nonce = uuid.UUID(data["pass"])
    except (signing.BadSignature, KeyError, ValueError, TypeError) as exc:
        raise NotFoundError("Pass is invalid.") from exc
    if not idempotency_key:
        raise ConflictError(
            "Idempotency-Key is required for offline events.", code="idempotency_key_required"
        )
    event, created = OfflineGateEvent.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "credential_nonce": nonce,
            "checkpoint": checkpoint[:100],
            "event_at": event_at,
            "recorded_by_user_id": actor_id,
        },
    )
    if not created and (event.credential_nonce != nonce or event.checkpoint != checkpoint):
        raise ConflictError(
            "Idempotency key was already used for a different event.", code="idempotency_conflict"
        )
    return event


def validate_pass(*, token, actor_id, checkpoint="", idempotency_key=""):
    presented_hash = _fingerprint(str(token))
    if idempotency_key:
        prior_attempt = GateAttempt.objects.filter(idempotency_key=idempotency_key).first()
        if prior_attempt:
            if (
                prior_attempt.presented_fingerprint != presented_hash
                or prior_attempt.checkpoint != checkpoint[:100]
            ):
                raise ConflictError(
                    "Idempotency key was already used for a different pass.",
                    code="idempotency_conflict",
                )
            if prior_attempt.result != "allowed" or not prior_attempt.request_id:
                raise ConflictError(
                    "This idempotency key was already used for a denied attempt.",
                    code="idempotency_conflict",
                )
            return VisitRequest.objects.get(pk=prior_attempt.request_id)
    try:
        data = signing.loads(token, salt="vms.visit-pass", max_age=60 * 60 * 24 * 120)
        nonce = uuid.UUID(data["pass"])
    except (signing.BadSignature, KeyError, ValueError, TypeError) as exc:
        _record_gate_attempt(
            token_fingerprint=presented_hash,
            checkpoint=checkpoint,
            failure_code="invalid_credential",
            actor_id=actor_id,
            idempotency_key=idempotency_key,
        )
        raise NotFoundError("Pass is invalid or expired.") from exc
    denial = None
    result = None
    with transaction.atomic():
        visit_pass = VisitPass.objects.select_for_update().filter(credential_nonce=nonce).first()
        now = timezone.now()
        if (
            visit_pass is None
            or visit_pass.status != "active"
            or visit_pass.valid_from > now
            or visit_pass.valid_until <= now
        ):
            failed_visit = (
                VisitRequest.objects.select_related("visitor")
                .filter(pk=visit_pass.request_id)
                .first()
                if visit_pass
                else None
            )
            _record_gate_attempt(
                request=failed_visit,
                token_fingerprint=presented_hash,
                checkpoint=checkpoint,
                failure_code="pass_not_valid",
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                at=now,
            )
            if failed_visit:
                VisitLog.objects.create(
                    request=failed_visit,
                    event_type="gate_denied",
                    occurred_at=now,
                    location=checkpoint[:160],
                    recorded_by_user_id=actor_id,
                    reason="pass_not_valid",
                )
            denial = ConflictError("Pass is not valid for entry.", code="pass_not_valid")
        else:
            visit = (
                VisitRequest.objects.select_for_update()
                .select_related("visitor")
                .get(pk=visit_pass.request_id)
            )
            document_pending = (
                visit.kind in {"pre_registered", "walk_in", "event"}
                and not visit.identity_documents.filter(scan_status="clean").exists()
            )
            failure_code = ""
            if document_pending:
                _record_gate_attempt(
                    request=visit,
                    token_fingerprint=presented_hash,
                    checkpoint=checkpoint,
                    failure_code="identity_document_not_cleared",
                    actor_id=actor_id,
                    idempotency_key=idempotency_key,
                    at=now,
                )
                denial = ConflictError(
                    "Identity document has not passed security scanning.",
                    code="identity_document_not_cleared",
                )
            elif _active_blacklist(visit.visitor.display_name, visit.visitor.id_fingerprint, now):
                _record_gate_attempt(
                    request=visit,
                    token_fingerprint=presented_hash,
                    checkpoint=checkpoint,
                    failure_code="blacklist_match",
                    actor_id=actor_id,
                    idempotency_key=idempotency_key,
                    at=now,
                )
                VisitLog.objects.create(
                    request=visit,
                    event_type="gate_denied",
                    occurred_at=now,
                    location=checkpoint[:160],
                    recorded_by_user_id=actor_id,
                    reason="blacklist_match",
                )
                denial = PermissionDeniedError("Pass is not valid for entry.")
            elif visit.event_id:
                event = EventRecord.objects.select_for_update().filter(pk=visit.event_id).first()
                failure_code, message = (
                    _event_entry_failure(event, now)
                    if event
                    else ("event_unavailable", "The event is not available for entry.")
                )
                if failure_code:
                    _record_gate_attempt(
                        request=visit,
                        token_fingerprint=presented_hash,
                        checkpoint=checkpoint,
                        failure_code=failure_code,
                        actor_id=actor_id,
                        idempotency_key=idempotency_key,
                        at=now,
                    )
                    VisitLog.objects.create(
                        request=visit,
                        event_type="gate_denied",
                        occurred_at=now,
                        location=checkpoint[:160],
                        recorded_by_user_id=actor_id,
                        reason=failure_code,
                    )
                    denial = ConflictError(message, code=failure_code)
                else:
                    denial = None
            if denial is None:
                try:
                    transition = resolve(visit.status, "check_in", "security")
                except ValueError as exc:
                    _record_gate_attempt(
                        request=visit,
                        token_fingerprint=presented_hash,
                        checkpoint=checkpoint,
                        failure_code="invalid_visit_state",
                        actor_id=actor_id,
                        idempotency_key=idempotency_key,
                        at=now,
                    )
                    denial = ConflictError(str(exc), code="invalid_visit_transition")
                else:
                    prior = visit.status
                    visit.status = transition.target
                    visit.save(update_fields=["status", "updated_at"])
                    VisitTransition.objects.create(
                        request=visit,
                        from_status=prior,
                        to_status=visit.status,
                        event="check_in",
                        actor_user_id=actor_id,
                        actor_kind="security",
                    )
                    VisitLog.objects.create(
                        request=visit,
                        event_type="entry",
                        occurred_at=now,
                        location=checkpoint[:160],
                        recorded_by_user_id=actor_id,
                    )
                    _queue_host_arrival(visit)
                    _record_gate_attempt(
                        request=visit,
                        token_fingerprint=presented_hash,
                        checkpoint=checkpoint,
                        result="allowed",
                        actor_id=actor_id,
                        idempotency_key=idempotency_key,
                        at=now,
                    )
                    _audit(
                        actor_id,
                        "security",
                        "gate.check_in",
                        visit,
                        after={"checkpoint": checkpoint[:100]},
                    )
                    result = visit
    if denial:
        raise denial
    return result


@transaction.atomic
def checkout_visit(*, visit_id, actor_id, actor_kind="security", location=""):
    visit = (
        VisitRequest.objects.select_for_update()
        .select_related("visitor")
        .filter(pk=visit_id)
        .first()
    )
    if visit is None:
        raise NotFoundError("Visit request not found.")
    try:
        event = "record_exit" if visit.status == "terminated" else "check_out"
        transition = resolve(visit.status, event, actor_kind)
    except ValueError as exc:
        raise ConflictError(str(exc), code="invalid_visit_transition") from exc
    now = timezone.now()
    prior = visit.status
    visit.status = transition.target
    visit.save(update_fields=["status", "updated_at"])
    VisitTransition.objects.create(
        request=visit,
        from_status=prior,
        to_status=visit.status,
        event=event,
        actor_user_id=actor_id,
        actor_kind=actor_kind,
    )
    VisitLog.objects.create(
        request=visit,
        event_type="exit",
        occurred_at=now,
        location=location[:160],
        recorded_by_user_id=actor_id,
    )
    NotificationOutbox.objects.get_or_create(
        dedupe_key=f"visit:{visit.pk}:checked-out:{now.isoformat()}",
        defaults={
            "topic": "visit.checked_out",
            "recipient_email": visit.visitor.email,
            "subject": "Visitor check-out recorded",
            "body": f"Check-out was recorded for visit request {visit.pk}.",
            "payload": {"visit_id": visit.pk},
        },
    )
    if visit.host_user_id:
        NotificationOutbox.objects.get_or_create(
            dedupe_key=f"visit:{visit.pk}:host-checked-out:{now.isoformat()}",
            defaults={
                "topic": "visit.checked_out",
                "recipient_user_id": visit.host_user_id,
                "subject": "Visitor has checked out",
                "body": f"Visit request {visit.pk} has been checked out.",
                "payload": {"visit_id": visit.pk},
            },
        )
    _audit(
        actor_id,
        actor_kind,
        "visit.check_out",
        visit,
        after={"location": location[:160], "at": now.isoformat()},
    )
    return visit
