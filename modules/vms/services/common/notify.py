"""Notification outbox (VMS-CFR-028, CFR-021). Writes rows; lane E delivers them."""
from __future__ import annotations

from modules.vms.models import IntegrationSetting, Notification

CHANNELS = {c.value for c in Notification.Channel}


def _enabled_channels(topic, channels):
    """Apply the notification_channels setting (BR-174). Accepts a flat
    {channel: bool} map, a list of enabled channels, or {topic: [channels]};
    a channel absent from a flat map stays enabled."""
    row = IntegrationSetting.objects.filter(key="notification_channels").first()
    value = row.value if row else None
    if isinstance(value, dict) and value and not all(
            isinstance(v, bool) for v in value.values()):
        value = value.get(topic, value.get("default", value.get("*")))
    if isinstance(value, (list, tuple, set)):
        return [c for c in channels if c in value]
    if isinstance(value, dict) and all(isinstance(v, bool) for v in value.values()):
        return [c for c in channels if value.get(c, True)]
    return list(channels)


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
    channels = _enabled_channels(topic, channels)
    for channel in dict.fromkeys(channels):   # order-preserving de-dup
        row, _ = Notification.objects.get_or_create(
            dedupe_key=f"{dedupe_key}:{channel}"[:200],
            defaults={"topic": topic, "recipient_user_id": user_id,
                      "recipient_visitor": visitor, "channel": channel,
                      "subject": subject[:200], "body": body,
                      "detail": detail or {}})
        rows.append(row)
    return rows
