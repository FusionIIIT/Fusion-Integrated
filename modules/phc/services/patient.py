from django.db import transaction
from rest_framework.exceptions import NotFound

from core.api.exceptions import BadRequestError
from modules.phc.models import PatientVisit, Prescription

@transaction.atomic
def record_visit(patient_user_id: int, visited_on, notes: str, recorded_by_user_id: int) -> PatientVisit:
    if not isinstance(visited_on, date):
        raise BadRequestError("Invalid date format for 'visited_on'")
    
    return PatientVisit.objects.create(
        patient_user_id=patient_user_id,
        visited_on=visited_on,
        notes=notes,
        recorded_by_user_id=recorded_by_user_id,
    )

@transaction.atomic
def issue_prescription(visit_id: int, details: str) -> Prescription:
    try:
        visit = PatientVisit.objects.get(id=visit_id)
    except PatientVisit.DoesNotExist:
        raise NotFound("Patient visit not found")
    
    return Prescription.objects.create(
        patient_visit=visit,
        details=details,
        issued_on=date.today(),
    )

@transaction.atomic
def export_medical_record_pdf(patient_user_id: int) -> bytes:
    from modules.phc.services.pdf import generate_medical_record_pdf
    
    try:
        visits = PatientVisit.objects.filter(patient_user_id=patient_user_id)
        prescriptions = Prescription.objects.filter(patient_visit__patient_user_id=patient_user_id)
    except Exception as e:
        raise BadRequestError(f"Failed to gather medical records: {e}")
    
    return generate_medical_record_pdf(visits, prescriptions)
