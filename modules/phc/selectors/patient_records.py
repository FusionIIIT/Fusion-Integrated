"""Patient medical records and prescription selectors (CFR-PHC-002, PHC-BR-02)."""
from django.db.models import Q

from modules.phc.domain.errors import UnauthorizedRecordAccessError
from modules.phc.models.patient_records import PatientVisit, Prescription


def get_patient_medical_history(patient_user_id: int) -> list[PatientVisit]:
    """Read-only access to a patient's own visit records (AFR-PHC-009, 012; PHC-BR-02)."""
    return list(
        PatientVisit.objects.filter(patient_user_id=patient_user_id)
        .select_related("doctor")
        .prefetch_related("prescriptions")
        .order_by("-visit_date", "-created_at")
    )


def get_patient_prescriptions(patient_user_id: int) -> list[Prescription]:
    """Read-only access to a patient's own prescriptions (AFR-PHC-010, 012; PHC-BR-02)."""
    return list(
        Prescription.objects.filter(patient_user_id=patient_user_id)
        .select_related("visit", "visit__doctor")
        .order_by("-prescribed_date", "-created_at")
    )


def get_patient_visit_by_id(visit_id: int, requesting_user_id: int, is_staff: bool = False) -> PatientVisit:
    """Enforces ownership unless caller is authorized PHC Staff (PHC-BR-02)."""
    visit = PatientVisit.objects.select_related("doctor").prefetch_related("prescriptions").get(id=visit_id)
    if not is_staff and visit.patient_user_id != requesting_user_id:
        raise UnauthorizedRecordAccessError(
            "PHC-BR-02: You are not authorized to view clinical records belonging to another patient."
        )
    return visit


def search_patient_records_staff(query: str = "") -> list[PatientVisit]:
    """Clinical lookup for PHC Staff (AFR-PHC-006; UC-PHC-06)."""
    qs = PatientVisit.objects.select_related("doctor").prefetch_related("prescriptions").all()
    if query:
        qs = qs.filter(
            Q(diagnosis__icontains=query)
            | Q(symptoms__icontains=query)
            | Q(doctor__name__icontains=query)
            | Q(prescriptions__prescription_number__icontains=query)
        ).distinct()
    return list(qs.order_by("-visit_date", "-created_at")[:50])
