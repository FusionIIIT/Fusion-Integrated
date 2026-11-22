"""Whose rows each acting role sees; out-of-scope rows are absent, so details 404 (PHC-BR-02)."""
from __future__ import annotations

from django.db.models import Prefetch, QuerySet

from modules.phc.models import (
    AmbulanceLog,
    ClaimAction,
    DoctorAttendance,
    DoctorSchedule,
    HealthAdvisory,
    InventoryItem,
    LowStockAlert,
    Notification,
    PatientVisit,
    Prescription,
    ReimbursementClaim,
    Requisition,
)

P_RECORD_CREATE = "phc.record.create"
P_CLAIM_CREATE = "phc.claim.create"
CLAIM_PROCESSOR_PERMISSIONS = ("phc.claim.review", "phc.claim.update", "phc.claim.approve")
P_SCHEDULE_MAINTAIN = ("phc.schedule.create", "phc.schedule.update", "phc.schedule.publish",
                       "phc.attendance.update")
P_REQUISITION_STAFF = ("phc.requisition.create", "phc.requisition.update")
P_REQUISITION_APPROVE = "phc.requisition.approve"


def _uid(actor) -> int | None:
    return getattr(actor, "user_id", None)


def _has(actor, *codes: str) -> bool:
    check = getattr(actor, "has_any_permission", None)
    return bool(check) and check(*codes)


def schedules_for(actor, *, today) -> QuerySet[DoctorSchedule]:
    # PHC-BR-01: patients see the published schedule with today's attendance only.
    qs = DoctorSchedule.objects.prefetch_related(
        "slots",
        Prefetch("attendance", queryset=DoctorAttendance.objects.filter(attendance_date=today),
                 to_attr="today_attendance"),
    )
    if not _has(actor, *P_SCHEDULE_MAINTAIN):
        qs = qs.filter(is_published=True)
    return qs.order_by("doctor_name", "id")


def visits_for(actor) -> QuerySet[PatientVisit]:
    # PHC-BR-02: PHC Staff manage every record except their own; a patient reads only theirs.
    uid = _uid(actor)
    if uid is None:
        return PatientVisit.objects.none()
    qs = PatientVisit.objects.prefetch_related("prescriptions")
    if _has(actor, P_RECORD_CREATE):
        return qs.exclude(patient_user_id=uid).order_by("-visit_date", "-id")
    return qs.filter(patient_user_id=uid).order_by("-visit_date", "-id")


def own_prescriptions(actor) -> QuerySet[Prescription]:
    uid = _uid(actor)
    if uid is None:
        return Prescription.objects.none()
    return Prescription.objects.filter(visit__patient_user_id=uid)


def claims_for(actor) -> QuerySet[ReimbursementClaim]:
    # A processing office never sees its own claim, so it can never appear in its own queue.
    uid = _uid(actor)
    if uid is None:
        return ReimbursementClaim.objects.none()
    qs = ReimbursementClaim.objects.select_related("prescription", "prescription__visit")
    qs = qs.prefetch_related(Prefetch("actions", queryset=ClaimAction.objects.order_by(
        "created_at", "id")))
    if _has(actor, *CLAIM_PROCESSOR_PERMISSIONS):
        return qs.exclude(user_id=uid).order_by("-submitted_at", "-id")
    if _has(actor, P_CLAIM_CREATE):
        return qs.filter(user_id=uid).order_by("-submitted_at", "-id")
    return ReimbursementClaim.objects.none()


def inventory_for(actor) -> QuerySet[InventoryItem]:
    return InventoryItem.objects.order_by("name")


def alerts_for(actor) -> QuerySet[LowStockAlert]:
    return LowStockAlert.objects.select_related("item").order_by("-created_at", "-id")


def requisitions_for(actor) -> QuerySet[Requisition]:
    uid = _uid(actor)
    if uid is None:
        return Requisition.objects.none()
    qs = Requisition.objects.prefetch_related("lines", "lines__item")
    if _has(actor, *P_REQUISITION_STAFF):
        return qs.order_by("-created_at", "-id")
    if _has(actor, P_REQUISITION_APPROVE):
        return qs.exclude(originator_user_id=uid).order_by("-created_at", "-id")
    return Requisition.objects.none()


def ambulance_logs_for(actor) -> QuerySet[AmbulanceLog]:
    return AmbulanceLog.objects.order_by("-used_at", "-id")


def advisories_for(actor) -> QuerySet[HealthAdvisory]:
    return HealthAdvisory.objects.order_by("-published_at", "-id")


def notifications_for(actor) -> QuerySet[Notification]:
    uid = _uid(actor)
    if uid is None:
        return Notification.objects.none()
    return Notification.objects.filter(recipient_user_id=uid).order_by("-created_at", "-id")
