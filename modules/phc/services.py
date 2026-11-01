from django.db import transaction
from rest_framework.exceptions import ValidationError

from modules.phc.models import Prescription, Visit


def publish_schedule(schedule):
    schedule.published = True
    schedule.save(update_fields=["published", "updated_at"])
    return schedule


def set_presence(schedule, is_present):
    if not schedule.published:
        raise ValidationError("Only a published schedule can be marked present.")
    schedule.is_present = is_present
    schedule.save(update_fields=["is_present", "updated_at"])
    return schedule


@transaction.atomic
def record_visit(recorded_by, prescriptions, **visit_data):
    visit_data["recorded_by"] = recorded_by
    visit = Visit.objects.create(**visit_data)
    if prescriptions:
        Prescription.objects.bulk_create(
            [Prescription(visit=visit, **p) for p in prescriptions]
        )
    return visit
