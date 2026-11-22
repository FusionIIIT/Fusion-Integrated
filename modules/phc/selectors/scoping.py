"""PHC selectors: ownership-scoped querysets.

Authorisation is enforced here, not in views, so the view always gets the
right scope and a foreign row is simply absent (→ 404, never 403 by mistake).
"""

from __future__ import annotations

from django.db.models import QuerySet

from modules.phc.models import (
    DoctorAttendance,
    DoctorSchedule,
    HealthAnnouncement,
    InventoryItem,
    PatientVisit,
    PhcNotification,
    Prescription,
    ProcurementRequisition,
    ReimbursementClaim,
)

# ---------------------------------------------------------------------------
# Schedule & Attendance
# ---------------------------------------------------------------------------


def published_schedules() -> QuerySet[DoctorSchedule]:
    """PHC-BR-01, AFR-PHC-003: published slots visible to patients."""
    return DoctorSchedule.objects.filter(is_published=True)


def all_schedules() -> QuerySet[DoctorSchedule]:
    """PHC Staff can see all slots (published or draft)."""
    return DoctorSchedule.objects.all()


def today_attendance(date) -> QuerySet[DoctorAttendance]:
    """Current-day attendance records (PHC-BR-01, AFR-PHC-004)."""
    return DoctorAttendance.objects.filter(date=date).select_related("schedule")


# ---------------------------------------------------------------------------
# Patient Records  (PHC-BR-02: ownership-scoped)
# ---------------------------------------------------------------------------


def patient_visits(patient_user_id: int) -> QuerySet[PatientVisit]:
    """PHC-BR-02: a patient may only see their own visits."""
    return PatientVisit.objects.filter(user_id=patient_user_id).order_by("-visit_date")


def all_visits() -> QuerySet[PatientVisit]:
    """PHC Staff see all visits (PHC-UC-06)."""
    return PatientVisit.objects.all().order_by("-visit_date")


def patient_prescriptions(patient_user_id: int) -> QuerySet[Prescription]:
    """PHC-BR-02: ownership-scoped prescription list."""
    return Prescription.objects.filter(user_id=patient_user_id).select_related("visit")


def all_prescriptions() -> QuerySet[Prescription]:
    return Prescription.objects.all().select_related("visit")


def visit_prescriptions(visit_id: int, patient_user_id: int) -> QuerySet[Prescription]:
    """Prescriptions for a specific visit, ownership-checked."""
    return Prescription.objects.filter(visit_id=visit_id, user_id=patient_user_id)


# ---------------------------------------------------------------------------
# Reimbursement Claims
# ---------------------------------------------------------------------------


def employee_claims(employee_user_id: int) -> QuerySet[ReimbursementClaim]:
    """PHC-UC-05, AFR-PHC-022: ownership-scoped claim list for the employee."""
    return (
        ReimbursementClaim.objects.filter(user_id=employee_user_id)
        .prefetch_related("audit_entries")
        .order_by("-submitted_at")
    )


def all_claims() -> QuerySet[ReimbursementClaim]:
    """PHC Staff, Accounts & Audit, Approving Authority: all claims."""
    return (
        ReimbursementClaim.objects.all().prefetch_related("audit_entries").order_by("-submitted_at")
    )


def claims_by_status(status: str) -> QuerySet[ReimbursementClaim]:
    return all_claims().filter(status=status)


# ---------------------------------------------------------------------------
# Inventory
# ---------------------------------------------------------------------------


def all_inventory() -> QuerySet[InventoryItem]:
    return InventoryItem.objects.all().order_by("name")


def low_stock_items() -> QuerySet[InventoryItem]:
    """Items strictly below their reorder threshold (PHC-BR-07)."""
    from django.db.models import F

    return InventoryItem.objects.filter(stock_quantity__lt=F("reorder_threshold"))


# ---------------------------------------------------------------------------
# Procurement Requisitions
# ---------------------------------------------------------------------------


def submitter_requisitions(user_id: int) -> QuerySet[ProcurementRequisition]:
    """PHC Staff sees their own requisitions (AFR-PHC-029 notification context)."""
    return (
        ProcurementRequisition.objects.filter(submitted_by_user_id=user_id)
        .prefetch_related("line_items")
        .order_by("-created_at")
    )


def all_requisitions() -> QuerySet[ProcurementRequisition]:
    return (
        ProcurementRequisition.objects.all().prefetch_related("line_items").order_by("-created_at")
    )


def pending_requisitions() -> QuerySet[ProcurementRequisition]:
    return all_requisitions().filter(status="pending_approval")


# ---------------------------------------------------------------------------
# Announcements
# ---------------------------------------------------------------------------


def patient_announcements() -> QuerySet[HealthAnnouncement]:
    """AFR-PHC-033: published advisories for patients' dashboards."""
    return HealthAnnouncement.objects.filter(is_published=True)


def all_announcements() -> QuerySet[HealthAnnouncement]:
    return HealthAnnouncement.objects.all()


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------


def pending_notifications(limit: int = 200) -> QuerySet[PhcNotification]:
    return PhcNotification.objects.filter(delivered=False).order_by("created_at")[:limit]


def recipient_notifications(user_id: int) -> QuerySet[PhcNotification]:
    return PhcNotification.objects.filter(recipient_user_id=user_id).order_by("-created_at")
