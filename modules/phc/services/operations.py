from django.db import transaction

from modules.phc.models import AmbulanceUsage, HealthAdvisory
from modules.phc.services.common import audit


def record_ambulance_usage(*, used_at, patient_name: str, destination: str,
                           actor_user_id: int) -> AmbulanceUsage:
    with transaction.atomic():
        row = AmbulanceUsage.objects.create(
            used_at=used_at, patient_name=patient_name,
            destination=destination, recorded_by_user_id=actor_user_id)
        audit(actor_user_id=actor_user_id, action="ambulance_usage.recorded",
              object_type="ambulance_usage", object_id=row.pk)
        return row


def publish_advisory(*, title: str, body: str, actor_user_id: int) -> HealthAdvisory:
    from django.utils import timezone

    with transaction.atomic():
        row = HealthAdvisory.objects.create(
            title=title, body=body, published_at=timezone.now(),
            published_by_user_id=actor_user_id)
        audit(actor_user_id=actor_user_id, action="advisory.published",
              object_type="health_advisory", object_id=row.pk)
        return row
