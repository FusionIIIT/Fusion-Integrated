from django.db import transaction

from core.api.exceptions import NotFoundError
from modules.directory.contracts import get_users
from modules.phc.models import PatientVisit, Prescription
from modules.phc.services.common import audit


def create_visit(*, patient_user_id: int, visited_on, notes: str,
                 prescription_details: str, issued_on, actor_user_id: int):
    if patient_user_id not in get_users([patient_user_id]):
        raise NotFoundError("Select a person from the institute directory.",
                            code="patient_not_found")
    with transaction.atomic():
        visit = PatientVisit.objects.create(
            patient_user_id=patient_user_id,
            visited_on=visited_on,
            notes=notes,
            recorded_by_user_id=actor_user_id,
        )
        prescription = Prescription.objects.create(
            visit=visit,
            details=prescription_details,
            issued_on=issued_on,
            issued_by_user_id=actor_user_id,
        )
        audit(actor_user_id=actor_user_id, action="patient_visit.created",
              object_type="patient_visit", object_id=visit.pk)
        audit(actor_user_id=actor_user_id, action="prescription.created",
              object_type="prescription", object_id=prescription.pk)
        return visit
