"""System-generated email triggers (PMS-AFR-192..205, BR-PMS-116).

PMS only triggers the email through Django's configured mail backend. Delivery
infrastructure is outside PMS, so a failure to send never fails the action that caused it.
"""
from __future__ import annotations

import logging
from collections.abc import Iterable

from django.conf import settings
from django.core.mail import send_mail

from modules.directory import contracts as directory

log = logging.getLogger("fusion.patents.notify")


def notify(user_ids: Iterable[int | None], application, subject: str, body: str) -> int:
    """Email the users who have an address in the directory. Returns how many were sent."""
    ids = sorted({int(i) for i in user_ids if i is not None})
    if not ids:
        return 0
    try:
        users = directory.get_users(ids)
    except Exception:
        log.exception("patents.notify.directory_failed application=%s", application.id)
        return 0
    emails = [users[i].email for i in ids if i in users and users[i].email]
    if not emails:
        log.warning("patents.notify.no_recipient application=%s users=%s", application.id, ids)
        return 0
    marker = f"[{application.application_number}] "
    try:
        return send_mail(
            subject=marker + subject,
            message=f"{body}\n\nPatent application {application.application_number}: "
                    f"{application.title}",
            from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
            recipient_list=emails,
            fail_silently=False,
        )
    except Exception:
        log.exception("patents.notify.send_failed application=%s", application.id)
        return 0
