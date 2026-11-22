"""Patient record and prescription writes (AFR-PHC-006..012)."""
from __future__ import annotations

from django.db import transaction

from core.api.exceptions import NotFoundError
from modules.phc.domain.pdf import render_pdf
from modules.phc.models import Patient, Prescription, Visit
from modules.phc.selectors import scoping
from modules.phc.services import audit

PATIENT_NOT_FOUND = "No matching patient was found. Check the patient list and try again."
VISIT_NOT_FOUND = "No matching visit was found for this patient. Refresh and try again."
RECORD_NOT_FOUND = "No matching record was found for your account."


def search(query: str):
    return scoping.patients_matching(query) if len(query) >= 2 else Patient.objects.none()


@transaction.atomic
def create_visit(actor, validated: dict) -> Visit:
    patient = scoping.patient_by_id(validated["patient_id"])
    if patient is None:
        raise NotFoundError(PATIENT_NOT_FOUND, code="not_found")
    visit = Visit.objects.create(
        patient=patient,
        user_id=patient.user_id,
        recorded_by=getattr(actor, "user_id", None),
        notes=validated.get("notes", ""),
    )
    audit.record(actor, "visit.create", "visit", visit.pk,
                 {"patient_id": visit.patient_id})
    return visit


@transaction.atomic
def create_prescription(actor, validated: dict) -> Prescription:
    visit = (Visit.objects
             .filter(pk=validated["visit_id"], patient_id=validated["patient_id"])
             .first())
    if visit is None:
        raise NotFoundError(VISIT_NOT_FOUND, code="not_found")
    prescription = Prescription.objects.create(
        visit=visit,
        patient_id=validated["patient_id"],
        user_id=validated["patient_id"],
        medicine=validated["medicine"],
        dosage=validated.get("dosage", ""),
        recorded_by=getattr(actor, "user_id", None),
    )
    audit.record(actor, "prescription.create", "prescription", prescription.pk,
                 {"patient_id": prescription.patient_id})
    return prescription


def record_copy(actor, pk: int) -> bytes:
    """Return a PDF copy of a visit the actor owns, or 404."""
    visit = scoping.visit_for_patient(pk, getattr(actor, "user_id", None))
    if visit is None:
        raise NotFoundError(RECORD_NOT_FOUND, code="not_found")
    prescriptions = scoping.prescriptions_for_visit(visit.patient_id, visit)
    lines = [
        "Primary Health Care - Patient Record Copy",
        f"Record ID: {visit.pk}",
        f"Patient ID: {visit.patient_id}",
        f"Visit date: {visit.visit_date.isoformat()}",
        "",
        "Consultation notes:",
        visit.notes or "(none)",
        "",
        "Prescriptions:",
    ]
    lines += [f"- {p.medicine} | {p.dosage or 'no dosage recorded'}"
              for p in prescriptions] or ["(none)"]
    return render_pdf(lines)
