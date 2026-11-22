"""Ambulance usage writes (AFR-PHC-032)."""
from __future__ import annotations

from django.db import transaction

from modules.phc.models import AmbulanceLog
from modules.phc.services import audit


@transaction.atomic
def log_usage(actor, validated: dict) -> AmbulanceLog:
    entry = AmbulanceLog.objects.create(
        timestamp=validated["timestamp"],
        patient_name=validated["patient_name"],
        destination=validated["destination"],
        user_id=getattr(actor, "user_id", None),
        logged_by=getattr(actor, "user_id", None),
    )
    audit.record(actor, "ambulance.log", "ambulance", entry.pk, {"logged": True})
    return entry
