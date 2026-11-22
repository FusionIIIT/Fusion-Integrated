"""Ambulance log (PHC-UC-11) and health advisories (PHC-UC-12)."""
from __future__ import annotations

from datetime import datetime

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError
from modules.phc.models import AmbulanceLog, HealthAdvisory


@transaction.atomic
def log_ambulance(*, actor, used_at: datetime, patient_name: str,
                  destination: str) -> AmbulanceLog:
    if used_at > timezone.now():
        raise BadRequestError("The ambulance use cannot be logged in the future.",
                              code="used_in_future")
    return AmbulanceLog.objects.create(used_at=used_at, patient_name=patient_name,
                                       destination=destination,
                                       recorded_by_user_id=actor.user_id)


@transaction.atomic
def publish_advisory(*, actor, title: str, body: str) -> HealthAdvisory:
    return HealthAdvisory.objects.create(title=title, body=body, published_at=timezone.now(),
                                         published_by_user_id=actor.user_id)
