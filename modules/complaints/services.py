import hashlib
import logging
import os
import uuid
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from core.files.validators import sanitise_filename
from modules.complaints.models import (
    Complaint,
    ComplaintAttachment,
    ComplaintNotification,
)

log = logging.getLogger("fusion.complaints.notify")


def _validate_attachments(attachments):
    max_size = getattr(settings, "COMPLAINT_ATTACHMENT_MAX_BYTES", None)
    allowed_types = getattr(settings, "COMPLAINT_ATTACHMENT_CONTENT_TYPES", ())
    cleaned = []
    max_count = getattr(settings, "COMPLAINT_ATTACHMENT_MAX_COUNT", None)
    if max_count is not None and len(attachments) > max_count:
        raise BadRequestError("Remove attachments until the configured count limit is met.",
                              code="too_many_attachments")
    for item in attachments:
        name = sanitise_filename(item.name)
        content_type = str(item.content_type or "application/octet-stream").strip().lower()
        size = item.size
        if (not content_type or not isinstance(size, int) or
                isinstance(size, bool) or size <= 0):
            raise BadRequestError("Each attachment needs a positive file size.",
                                  code="invalid_attachment")
        if not name or name == "upload":
            raise BadRequestError("Give each attachment a valid file name.",
                                  code="invalid_attachment_name")
        if max_size is not None and size > max_size:
            raise BadRequestError("An attachment exceeds the configured size limit.",
                                  code="attachment_too_large")
        if allowed_types and content_type not in allowed_types:
            raise BadRequestError("An attachment has a file type that is not accepted.",
                                  code="attachment_type_not_allowed")
        cleaned.append((item, name, content_type, size))
    return cleaned


def _store_file(upload, *, storage_key):
    root = Path(settings.COMPLAINT_ATTACHMENT_ROOT).expanduser().resolve()
    base = Path(settings.BASE_DIR).resolve()
    if root == base or base in root.parents:
        raise RuntimeError("Complaint attachment storage must be outside the project tree.")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if os.name != "nt":
        root.chmod(0o700)
    first = root / storage_key[:2]
    second = first / storage_key[2:4]
    first.mkdir(mode=0o700, exist_ok=True)
    second.mkdir(mode=0o700, exist_ok=True)
    if first.resolve().parent != root or second.resolve().parent != first.resolve():
        raise RuntimeError("Complaint attachment storage path escaped its root.")
    if os.name != "nt":
        first.chmod(0o700)
        second.chmod(0o700)
    target = second / storage_key
    descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    digest = hashlib.sha256()
    try:
        with os.fdopen(descriptor, "wb") as output:
            for chunk in upload.chunks():
                output.write(chunk)
                digest.update(chunk)
    except Exception:
        target.unlink(missing_ok=True)
        raise
    return digest.hexdigest()


@transaction.atomic
def submit(*, user_id: int, recipient_email: str, category: str,
           description: str, attachments=()):
    category = category.strip()
    description = description.strip()
    if not category or not description:
        raise BadRequestError("Enter a complaint category and description.",
                              code="required_fields")
    if len(category) > 120:
        raise BadRequestError("Complaint category must be 120 characters or fewer.",
                              code="category_too_long")
    prepared = _validate_attachments(attachments)
    complaint = Complaint.objects.create(
        complainant_user_id=user_id,
        category=category,
        description=description,
        submitted_at=timezone.now(),
    )
    written = []
    try:
        rows = []
        for upload, name, content_type, size in prepared:
            key = uuid.uuid4().hex
            digest = _store_file(upload, storage_key=key)
            written.append(key)
            rows.append(ComplaintAttachment(
                complaint=complaint, name=name, content_type=content_type,
                size_bytes=size, storage_key=key, sha256=digest,
            ))
        ComplaintAttachment.objects.bulk_create(rows)
    except Exception:
        root = Path(settings.COMPLAINT_ATTACHMENT_ROOT).expanduser().resolve()
        for key in written:
            (root / key[:2] / key[2:4] / key).unlink(missing_ok=True)
        raise
    ComplaintNotification.objects.create(
        complaint=complaint, recipient_user_id=user_id,
        recipient_email=recipient_email,
    )
    return complaint


def deliver_pending(*, limit=100):
    now = timezone.now()
    ComplaintNotification.objects.filter(
        status="sending", claimed_at__lt=now - timedelta(minutes=10),
    ).update(status="pending", claimed_at=None)
    pending = ComplaintNotification.objects.filter(status="pending").order_by(
        "created_at")[:limit]
    report = {"sent": 0, "failed": 0, "deferred": 0}
    for row in pending:
        claimed = ComplaintNotification.objects.filter(
            pk=row.pk, status="pending").update(status="sending", claimed_at=now)
        if not claimed:
            report["deferred"] += 1
            continue
        try:
            if not row.recipient_email:
                raise ValueError("No email address was available at submission.")
            send_mail(
                subject=f"Complaint received: {row.complaint.public_id}",
                message=(f"Your complaint {row.complaint.public_id} was received "
                         f"at {row.complaint.submitted_at.isoformat()}."),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[row.recipient_email], fail_silently=False,
            )
        except Exception as exc:
            row.attempts += 1
            row.last_error = f"{exc.__class__.__name__}: {exc}"[:300]
            max_attempts = settings.COMPLAINT_NOTIFICATION_MAX_ATTEMPTS
            row.status = "failed" if row.attempts >= max_attempts else "pending"
            row.claimed_at = None
            row.save(update_fields=["attempts", "last_error", "status", "claimed_at",
                                    "updated_at"])
            report["failed"] += 1
            continue
        row.status = "sent"
        row.sent_at = timezone.now()
        row.attempts += 1
        row.last_error = ""
        row.claimed_at = None
        row.save(update_fields=["status", "sent_at", "attempts", "last_error", "claimed_at",
                                "updated_at"])
        report["sent"] += 1
    if report["failed"]:
        log.warning("complaints.notify.failed count=%d", report["failed"])
    return report
