"""Patient Visit and Prescription services (CFR-PHC-002, UC-PHC-06, BR-PHC-09)."""
from datetime import date
from django.utils import timezone

from modules.phc.models.doctors import Doctor
from modules.phc.models.patient_records import PatientVisit, Prescription
from modules.phc.services.audit import record_audit_event


def create_patient_visit(
    patient_user_id: int,
    symptoms: str,
    diagnosis: str,
    created_by_user_id: int,
    created_by_username: str,
    doctor_id: int | None = None,
    visit_date: date | None = None,
    notes: str = "",
) -> PatientVisit:
    doctor = Doctor.objects.get(id=doctor_id) if doctor_id else None
    visit = PatientVisit.objects.create(
        patient_user_id=patient_user_id,
        doctor=doctor,
        visit_date=visit_date or timezone.now().date(),
        symptoms=symptoms.strip(),
        diagnosis=diagnosis.strip(),
        notes=notes.strip(),
        created_by_user_id=created_by_user_id,
    )
    # BR-09: Immutable audit trail for sensitive patient record creation
    record_audit_event(
        target_type="PATIENT_RECORD",
        target_id=visit.id,
        action="CREATE_VISIT",
        details={
            "patient_user_id": patient_user_id,
            "doctor": doctor.name if doctor else "N/A",
            "diagnosis": diagnosis,
        },
        actor_user_id=created_by_user_id,
        actor_username=created_by_username,
    )
    return visit


def create_prescription(
    visit_id: int,
    prescription_number: str,
    medicines_prescribed: str,
    created_by_user_id: int,
    created_by_username: str,
    prescribed_date: date | None = None,
    scanned_document_url: str = "",
    notes: str = "",
) -> Prescription:
    visit = PatientVisit.objects.get(id=visit_id)
    prescription = Prescription.objects.create(
        visit=visit,
        patient_user_id=visit.patient_user_id,
        prescription_number=prescription_number.strip(),
        prescribed_date=prescribed_date or timezone.now().date(),
        medicines_prescribed=medicines_prescribed.strip(),
        scanned_document_url=scanned_document_url.strip(),
        notes=notes.strip(),
        created_by_user_id=created_by_user_id,
    )
    # BR-09: Immutable audit trail for prescription digitization
    record_audit_event(
        target_type="PATIENT_RECORD",
        target_id=prescription.prescription_number,
        action="CREATE_PRESCRIPTION",
        details={
            "visit_id": visit.id,
            "patient_user_id": visit.patient_user_id,
            "has_scanned_doc": bool(scanned_document_url),
        },
        actor_user_id=created_by_user_id,
        actor_username=created_by_username,
    )
    return prescription
