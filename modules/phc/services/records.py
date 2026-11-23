"""Patient visits and prescriptions (PHC-UC-06) and the patient's PDF copy (PHC-UC-03)."""
from __future__ import annotations

from datetime import date

from django.db import transaction
from django.utils import timezone

from core.api.exceptions import BadRequestError, ConflictError, NotFoundError
from modules.directory import contracts as directory
from modules.phc.domain import pdf
from modules.phc.models import PatientVisit, Prescription
from modules.phc.services import trail


@transaction.atomic
def record_visit(*, actor, patient_user_id: int, visit_date: date, complaint: str,
                 diagnosis: str, prescriptions: list[dict]) -> PatientVisit:
    if patient_user_id == actor.user_id:
        raise ConflictError("You cannot record a visit for yourself; ask another PHC staff "
                            "member.", code="self_record")
    if visit_date > timezone.localdate():
        raise BadRequestError("The visit date cannot be in the future.",
                              code="visit_in_future")
    if not prescriptions:
        raise BadRequestError("Enter the prescription from the visit.",
                              code="prescription_required")
    texts = [complaint, diagnosis] + [str(v or "") for p in prescriptions
                                      for v in (p.get("medicine"), p.get("dosage"),
                                                p.get("instructions"))]
    # PHC-UC-03: the patient's PDF copy must reproduce every character it was given.
    if not all(pdf.printable(t) for t in texts):
        raise BadRequestError("Enter the record in English letters, digits and common "
                              "punctuation; the PDF copy cannot print other scripts yet.",
                              code="unprintable_text")
    if patient_user_id not in directory.get_users([patient_user_id]):
        raise NotFoundError("No patient profile matches that person.", code="unknown_patient")
    visit = PatientVisit.objects.create(patient_user_id=patient_user_id, visit_date=visit_date,
                                        complaint=complaint, diagnosis=diagnosis,
                                        recorded_by_user_id=actor.user_id)
    Prescription.objects.bulk_create(Prescription(visit=visit, **p) for p in prescriptions)
    # PHC-BR-09
    trail.audit(actor_user_id=actor.user_id, resource_type="patient_visit",
                resource_id=visit.pk, action="create",
                details={"prescriptions": len(prescriptions)})
    return visit


def records_pdf(visits: list[PatientVisit]) -> bytes:
    lines = ["Primary Health Centre - Medical Records", ""]
    for visit in visits:
        lines += [f"Visit on {visit.visit_date.isoformat()}",
                  f"Complaint: {visit.complaint}",
                  f"Diagnosis: {visit.diagnosis or 'Not recorded'}",
                  "Prescriptions:"]
        for p in visit.prescriptions.all():
            days = f", {p.duration_days} days" if p.duration_days else ""
            lines.append(f"  {p.medicine} - {p.dosage}{days}")
            if p.instructions:
                lines.append(f"    {p.instructions}")
        lines.append("")
    return pdf.render(lines)
