from django.db import transaction, IntegrityError
from core.api.exceptions import BadRequestError  # Updated import
from modules.phc.models import PatientVisit, Prescription, AuditEvent
from modules.phc.services.common import record_audit

def record_patient_visit_and_prescription(patient_user_id: int, notes: str, prescription_details: str, recorded_by_user_id: int) -> None:
    if not notes or not prescription_details:
        raise BadRequestError("Notes and prescription details cannot be blank")  # Updated arguments

    with transaction.atomic():
        visit = PatientVisit.objects.create(
            patient_user_id=patient_user_id,
            visited_on=None,  # This will be set by the database trigger
            notes=notes,
            recorded_by_user_id=recorded_by_user_id
        )

        prescription = Prescription.objects.create(
            patient_visit=visit,
            details=prescription_details,
            issued_on=None  # This will be set by the database trigger
        )

        record_audit("PatientVisit", visit.id, "CREATE", actor_user_id=recorded_by_user_id)
        record_audit("Prescription", prescription.id, "CREATE", actor_user_id=recorded_by_user_id)

def generate_medical_record_pdf(patient_user_id: int) -> bytes:
    from io import BytesIO
    from reportlab.pdfgen import canvas

    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    p.drawString(100, 750, "Medical Record")
    p.drawString(100, 730, f"Patient ID: {patient_user_id}")

    # Add visits and prescriptions here
    # For example:
    # p.drawString(100, 710, "Visit on 2023-04-01")
    # p.drawString(100, 690, "Prescription: Paracetamol")

    p.showPage()
    p.save()

    buffer.seek(0)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    if not pdf_bytes:
        raise Exception("Failed to generate PDF")

    return pdf_bytes
