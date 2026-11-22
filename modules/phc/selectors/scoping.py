"""All PHC reads start here; ownership is a narrowed queryset, never a later check."""
from __future__ import annotations

from django.db.models import QuerySet

from modules.phc.models import (
    AmbulanceLog,
    AuditLog,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    Patient,
    Prescription,
    ReimbursementClaim,
    Requisition,
    StockAdjustment,
    Visit,
)

P_RECORDS_MANAGE = "phc.records.manage"
P_SCHEDULE_MANAGE = "phc.schedule.manage"
P_INV_ADJUST = "phc.inventory.adjust"
P_AUDIT_VIEW = "phc.audit.view"
P_CLAIM_REVIEW = "phc.reimbursement.review"
P_CLAIM_VERIFY = "phc.reimbursement.verify"
P_CLAIM_SANCTION = "phc.reimbursement.sanction"
P_CLAIM_PAYMENT = "phc.reimbursement.payment"
P_REQ_DECIDE = "phc.requisition.decide"
P_REQ_FULFILL = "phc.requisition.fulfill"

STAFF_SCOPE = (P_RECORDS_MANAGE, P_SCHEDULE_MANAGE, P_INV_ADJUST,
               P_CLAIM_REVIEW, P_CLAIM_VERIFY, P_CLAIM_SANCTION,
               P_CLAIM_PAYMENT, P_REQ_DECIDE, P_REQ_FULFILL)


def _own_id(actor) -> int | None:
    return getattr(actor, "user_id", None)


def is_staff(actor) -> bool:
    """True only for an actor carrying a PHC staff-scope permission."""
    check = getattr(actor, "has_permission", None)
    return bool(check) and any(check(code) for code in STAFF_SCOPE)


def published_schedules() -> QuerySet[DoctorSchedule]:
    return DoctorSchedule.objects.filter(is_published=True)


def attendance_on(date) -> QuerySet[DoctorAttendance]:
    return DoctorAttendance.objects.filter(date=date)


def patients_matching(query: str) -> QuerySet[Patient]:
    return (Patient.objects.filter(display_name__icontains=query)
            .order_by("display_name")[:25])


def patient_by_id(user_id: int) -> Patient | None:
    return Patient.objects.filter(pk=user_id).first()


def visits_for(actor) -> QuerySet[Visit]:
    owner = _own_id(actor)
    return (Visit.objects.filter(patient_id=owner).order_by("-visit_date")
            if owner is not None else Visit.objects.none())


def visits_for_patient(user_id: int) -> QuerySet[Visit]:
    return Visit.objects.filter(patient_id=user_id).order_by("-visit_date")


def visit_for_patient(pk: int, user_id: int) -> Visit | None:
    return Visit.objects.filter(pk=pk, patient_id=user_id).first()


def prescriptions_for(actor) -> QuerySet[Prescription]:
    owner = _own_id(actor)
    return (Prescription.objects.filter(patient_id=owner).order_by("-created_at")
            if owner is not None else Prescription.objects.none())


def prescriptions_for_visit(user_id: int, visit: Visit) -> QuerySet[Prescription]:
    return Prescription.objects.filter(patient_id=user_id, visit=visit)


def claim_by_id(pk: int) -> ReimbursementClaim | None:
    return ReimbursementClaim.objects.filter(pk=pk).first()


def claims_for(actor) -> QuerySet[ReimbursementClaim]:
    owner = _own_id(actor)
    return (ReimbursementClaim.objects.filter(employee_id=owner)
            .order_by("-created_at") if owner is not None
            else ReimbursementClaim.objects.none())


def prescription_for_claimant(pk: int, user_id: int) -> Prescription | None:
    return Prescription.objects.filter(pk=pk, patient_id=user_id).first()


def inventory_items() -> QuerySet[InventoryItem]:
    return InventoryItem.objects.order_by("name")


def item_by_id(pk: int) -> InventoryItem | None:
    return InventoryItem.objects.filter(pk=pk).first()


def published_advisories() -> QuerySet[HealthAdvisory]:
    return HealthAdvisory.objects.filter(is_published=True).order_by("-published_at")


def audit_logs(limit: int) -> QuerySet[AuditLog]:
    return AuditLog.objects.all()[:limit]


def requisitions_for(actor) -> QuerySet[Requisition]:
    owner = _own_id(actor)
    if is_staff(actor):
        return Requisition.objects.order_by("-created_at")
    return (Requisition.objects.filter(originator_id=owner).order_by("-created_at")
            if owner is not None else Requisition.objects.none())


def stock_adjustments() -> QuerySet[StockAdjustment]:
    return StockAdjustment.objects.order_by("-created_at")


def ambulance_logs() -> QuerySet[AmbulanceLog]:
    return AmbulanceLog.objects.order_by("-timestamp")


def patient_counts_by_kind() -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in Patient.objects.values_list("kind", flat=True):
        counts[row] = counts.get(row, 0) + 1
    return counts
