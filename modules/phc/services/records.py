"""PHC services: patient visit records and prescriptions.

PHC-UC-06, AFR-PHC-006 … AFR-PHC-012, PHC-BR-02, PHC-BR-09.
"""

from __future__ import annotations

import logging
from datetime import date as date_type

from django.db import transaction

from modules.directory import contracts as directory_contracts
from modules.phc.models import (
    PatientRecordAudit,
    PatientVisit,
    Prescription,
)

log = logging.getLogger("fusion.phc.records")


def search_patients(*, query: str, limit: int = 25) -> list[dict]:
    """Search active student and employee profiles through directory's contract."""
    patients = []
    for kind in ("student", "faculty", "staff"):
        patients.extend(directory_contracts.search(query, kind=kind, limit=limit))
    patients.sort(key=lambda person: person.display_name.casefold())
    return [
        {
            "user_id": person.user_id,
            "username": person.username,
            "display_name": person.display_name,
            "kind": person.kind,
        }
        for person in patients[:limit]
    ]


def create_visit(
    *,
    patient_user_id: int,
    visit_date: date_type,
    chief_complaint: str,
    diagnosis: str = "",
    notes: str = "",
    actor_user_id: int,
) -> PatientVisit:
    """PHC-UC-06, AFR-PHC-006: Create a patient visit record."""
    with transaction.atomic():
        visit = PatientVisit.objects.create(
            user_id=patient_user_id,
            visit_date=visit_date,
            chief_complaint=chief_complaint,
            diagnosis=diagnosis,
            notes=notes,
            recorded_by_user_id=actor_user_id,
        )
        PatientRecordAudit.objects.create(
            record_type="visit",
            record_id=visit.pk,
            patient_user_id=patient_user_id,
            action="create",
            actor_user_id=actor_user_id,
            details={"visit_date": str(visit_date), "chief_complaint": chief_complaint},
        )
    log.info(
        "phc.visit.created visit=%s patient=%s by=%s", visit.pk, patient_user_id, actor_user_id
    )
    return visit


def add_prescription(
    *,
    visit: PatientVisit,
    medicine_name: str,
    dosage: str,
    duration_days: int | None = None,
    instructions: str = "",
    expense_date: date_type | None = None,
    actor_user_id: int,
) -> Prescription:
    """PHC-UC-06, AFR-PHC-008: Digitize a prescription linked to a visit."""
    with transaction.atomic():
        rx = Prescription.objects.create(
            visit=visit,
            user_id=visit.user_id,
            medicine_name=medicine_name,
            dosage=dosage,
            duration_days=duration_days,
            instructions=instructions,
            expense_date=expense_date,
            prescribed_by_user_id=actor_user_id,
        )
        PatientRecordAudit.objects.create(
            record_type="prescription",
            record_id=rx.pk,
            patient_user_id=visit.user_id,
            action="create",
            actor_user_id=actor_user_id,
            details={"medicine_name": medicine_name, "visit_id": visit.pk},
        )
    log.info("phc.prescription.created rx=%s visit=%s by=%s", rx.pk, visit.pk, actor_user_id)
    return rx
