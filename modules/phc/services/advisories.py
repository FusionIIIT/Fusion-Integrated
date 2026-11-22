"""Health advisory writes (AFR-PHC-033)."""
from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from modules.phc.models import HealthAdvisory
from modules.phc.services import audit


@transaction.atomic
def publish(actor, validated: dict) -> HealthAdvisory:
    advisory = HealthAdvisory.objects.create(
        title=validated["title"],
        content=validated["content"],
        user_id=getattr(actor, "user_id", None),
        is_published=True,
        published_at=timezone.now(),
        published_by=getattr(actor, "user_id", None),
    )
    audit.record(actor, "advisory.publish", "advisory", advisory.pk,
                 {"title": advisory.title})
    return advisory
