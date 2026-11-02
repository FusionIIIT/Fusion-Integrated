"""Notification outbox (VMS-CFR-028, CFR-021). Writes rows; lane E delivers them."""
from __future__ import annotations

from modules.vms.models import Notification

CHANNELS = {c.value for c in Notification.Channel}


def enqueue(*, topic, dedupe_key, subject, body, user_id=None, visitor=None,
            channels=("inapp", "email"), detail=None) -> list[Notification]:
    """One row per channel, idempotent: a repeated call returns the existing rows.

    The stored dedupe key is ``<dedupe_key>:<channel>`` because the column is
    unique and a message has one row per channel.
    """
    if user_id is None and visitor is None:
        raise ValueError("notify.enqueue needs a user_id or a visitor")
    unknown = set(channels) - CHANNELS
    if unknown:
        raise ValueError(f"unknown channel(s): {sorted(unknown)}")
    rows = []
    for channel in dict.fromkeys(channels):   # order-preserving de-dup
        row, _ = Notification.objects.get_or_create(
            dedupe_key=f"{dedupe_key}:{channel}"[:200],
            defaults={"topic": topic, "recipient_user_id": user_id,
                      "recipient_visitor": visitor, "channel": channel,
                      "subject": subject[:200], "body": body,
                      "detail": detail or {}})
        rows.append(row)
    return rows
