from datetime import timedelta

from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.vms.models import NotificationOutbox, VisitRequest, VisitTransition
from modules.vms.services.visits import checkout_visit


def expire_overdue(*, limit=500):
    now = timezone.now()
    ids = list(
        VisitRequest.objects.filter(
            status__in=["pending", "pending_admin_contingency", "pending_urgent_review"],
            approval_due_at__lte=now,
        )
        .order_by("approval_due_at")
        .values_list("pk", flat=True)[:limit]
    )
    changed = 0
    for visit_id in ids:
        with transaction.atomic():
            visit = (
                VisitRequest.objects.select_for_update()
                .filter(
                    pk=visit_id,
                    status__in=["pending", "pending_admin_contingency", "pending_urgent_review"],
                    approval_due_at__lte=now,
                )
                .first()
            )
            if visit is None:
                continue
            prior = visit.status
            event = {
                "pending": "expire",
                "pending_admin_contingency": "expire_contingency",
                "pending_urgent_review": "expire_urgent",
            }[prior]
            visit.status = "expired"
            visit.save(update_fields=["status", "updated_at"])
            VisitTransition.objects.create(
                request=visit,
                from_status=prior,
                to_status="expired",
                event=event,
                actor_kind="system",
            )
            NotificationOutbox.objects.get_or_create(
                dedupe_key=f"visit:{visit.pk}:expired",
                defaults={
                    "topic": "visit.expired",
                    "recipient_email": visit.visitor.email,
                    "subject": "Visitor request expired",
                    "body": f"Visit request {visit.pk} expired because it was not decided in time.",
                },
            )
            changed += 1
    return changed


def expire_passes(*, limit=500):
    from modules.vms.models import VisitPass

    return (
        VisitPass.objects.filter(status="active", valid_until__lte=timezone.now())
        .order_by("valid_until")
        .update(status="expired")
        if limit > 0
        else 0
    )


def expire_on_site_visits(*, limit=500):
    now = timezone.now()
    ids = list(
        VisitRequest.objects.filter(status="on_site", ends_at__lte=now)
        .order_by("ends_at")
        .values_list("pk", flat=True)[:limit]
    )
    count = 0
    for visit_id in ids:
        try:
            checkout_visit(
                visit_id=visit_id,
                actor_id=None,
                actor_kind="system",
                location="scheduled auto-checkout",
            )
            count += 1
        except ConflictError:
            # Another worker or gate may have changed the visit concurrently.
            continue
    return count


def queue_approval_reminders(*, limit=500):
    now = timezone.now()
    pending = (
        VisitRequest.objects.filter(status="pending")
        .select_related("visitor", "policy_version")
        .order_by("submitted_at")[:limit]
    )
    queued = 0
    for visit in pending:
        offsets = visit.policy_version.reminder_minutes if visit.policy_version_id else []
        elapsed_minutes = int((now - visit.submitted_at).total_seconds() // 60)
        for offset in offsets:
            if elapsed_minutes < int(offset):
                continue
            _, created = NotificationOutbox.objects.get_or_create(
                dedupe_key=f"visit:{visit.pk}:reminder:{int(offset)}",
                defaults={
                    "topic": "visit.approval_reminder",
                    "recipient_user_id": visit.host_user_id,
                    "subject": "Visitor request is still awaiting your decision",
                    "body": f"Visit request {visit.pk} remains pending host approval.",
                    "payload": {"visit_id": visit.pk, "reminder_offset": int(offset)},
                },
            )
            queued += int(created)
    return queued


def send_pending(*, limit=100):
    from urllib.parse import quote

    from django.conf import settings
    from django.core import signing
    from django.core.mail import send_mail

    from modules.vms.models import VisitorAccessCredential, VisitPass

    now = timezone.now()
    NotificationOutbox.objects.filter(
        status="sending", claimed_at__lt=now - timedelta(minutes=10)
    ).update(status="failed", next_attempt_at=now, last_error="stale_delivery_claim")
    eligible = NotificationOutbox.objects.filter(status__in=["pending", "failed"]).filter(
        Q(next_attempt_at__isnull=True) | Q(next_attempt_at__lte=now)
    )
    ids = list(eligible.order_by("created_at").values_list("pk", flat=True)[:limit])
    sent = 0
    for row_id in ids:
        with transaction.atomic():
            row = (
                NotificationOutbox.objects.select_for_update()
                .filter(pk=row_id, status__in=["pending", "failed"])
                .first()
            )
            if row is None:
                continue
            row.status = "sending"
            row.attempts = F("attempts") + 1
            row.claimed_at = now
            row.save(update_fields=["status", "attempts", "claimed_at"])
            row.refresh_from_db(fields=["attempts", "recipient_email", "subject", "body"])
            payload = row.payload or {}
            topic = row.topic
        body = row.body
        if topic == "visit.visitor_access":
            from django.core import signing

            credential = VisitorAccessCredential.objects.filter(
                pk=payload.get("credential_id"),
                revoked_at__isnull=True,
                expires_at__gt=timezone.now(),
            ).first()
            if credential is None:
                NotificationOutbox.objects.filter(pk=row_id).update(
                    status="suppressed", body="", payload={}, last_error="Credential unavailable"
                )
                continue
            visitor_token = signing.dumps(
                {"credential": str(credential.nonce)}, salt="vms.visitor-access", compress=True
            )
            base_url = settings.VMS_PUBLIC_BASE_URL.rstrip("/")
            body += (
                f"\n\nOpen your visitor portal: {base_url}/vms/access"
                f"?token={quote(visitor_token, safe='')}\n"
            )
        elif topic == "visit.approved":
            visit_pass = VisitPass.objects.filter(
                request_id=payload.get("visit_id"), status="active"
            ).first()
            if visit_pass is None:
                NotificationOutbox.objects.filter(pk=row_id).update(
                    status="suppressed", body="", payload={}, last_error="Pass unavailable"
                )
                continue
            token = signing.dumps(
                {"pass": str(visit_pass.credential_nonce)}, salt="vms.visit-pass", compress=True
            )
            body += f"\n\nPass QR credential: {token}"
        recipient_email = row.recipient_email
        if not recipient_email and row.recipient_user_id:
            from modules.directory import contracts as directory

            recipient = directory.get_users([row.recipient_user_id]).get(row.recipient_user_id)
            recipient_email = recipient.email if recipient else ""
        if not recipient_email:
            NotificationOutbox.objects.filter(pk=row_id).update(
                status="suppressed", body="", payload={}, last_error="No email address available"
            )
            continue
        try:
            send_mail(
                row.subject,
                body,
                settings.DEFAULT_FROM_EMAIL,
                [recipient_email],
                fail_silently=False,
            )
        # Mail backends can raise provider-specific exceptions; mark just this
        # outbox item failed and let the bounded retry schedule handle it.
        except Exception as exc:  # noqa: BLE001
            backoff = min(2 ** min(row.attempts, 10), 360) * 60
            NotificationOutbox.objects.filter(pk=row_id).update(
                status="failed",
                next_attempt_at=now + timedelta(minutes=backoff),
                last_error=type(exc).__name__[:300],
            )
        else:
            NotificationOutbox.objects.filter(pk=row_id).update(
                status="sent", sent_at=timezone.now(), body="", payload={}, last_error=""
            )
            sent += 1
    return sent
