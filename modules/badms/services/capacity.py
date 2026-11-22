from __future__ import annotations

import logging

from django.conf import settings
from django.utils import timezone

from modules.badms.models import (
    ArchivalRequest,
    StorageExtensionRequest,
    StorageObservation,
)
from modules.badms.services import audit, notifications, storage

log = logging.getLogger("fusion.badms.capacity")


def _observed_user_ids() -> list[int]:
    user_ids = set(
        ArchivalRequest.objects.values_list("requester_user_id", flat=True),
    )
    user_ids.update(
        StorageExtensionRequest.objects.values_list("requester_user_id", flat=True),
    )
    user_ids.update(StorageObservation.objects.values_list("user_id", flat=True))
    return sorted(user_ids)


def monitor_storage() -> int:
    threshold = settings.BADMS_STORAGE_THRESHOLD_PERCENT
    quota = settings.BADMS_USER_QUOTA_BYTES
    if not 1 <= threshold <= 100 or quota <= 0:
        raise ValueError("BADMS storage quota and threshold settings are invalid.")

    monitored = 0
    for user_id in _observed_user_ids():
        previous = StorageObservation.objects.filter(user_id=user_id).order_by(
            "-observed_at",
        ).first()
        try:
            used = storage.user_usage_bytes(user_id)
        except storage.StorageError as exc:
            log.error("badms.capacity.measurement_failed user_id=%s error_code=%s",
                      user_id, exc.code)
            audit.record(
                actor_user_id=None,
                action="capacity_measurement_failed",
                resource="storage",
                resource_id=str(user_id),
                outcome="failure",
                details={"error_code": exc.code},
            )
            continue

        StorageObservation.objects.create(
            user_id=user_id,
            used_bytes=used,
            quota_bytes=quota,
        )
        monitored += 1
        was_over_threshold = (
            previous is not None
            and previous.used_bytes * 100 >= previous.quota_bytes * threshold
        )
        is_over_threshold = used * 100 >= quota * threshold
        if is_over_threshold and not was_over_threshold:
            ratio = round(100 * used / quota, 1)
            subject = "BADMS storage threshold reached"
            body = (
                f"User {user_id} has reached {ratio}% of their configured "
                f"storage quota ({used} of {quota} bytes). "
                f"Observed at {timezone.now().isoformat()}."
            )
            notifications.enqueue_emails(
                recipients=settings.BADMS_SYSADMIN_EMAILS,
                subject=subject,
                body=body,
                resource="storage",
                resource_id=str(user_id),
            )
            audit.record(
                actor_user_id=None,
                action="storage_threshold_reached",
                resource="storage",
                resource_id=str(user_id),
                details={
                    "used_bytes": used,
                    "quota_bytes": quota,
                    "threshold_percent": threshold,
                },
            )
    return monitored
