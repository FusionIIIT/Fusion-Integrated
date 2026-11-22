from django.db.models import QuerySet

from modules.phc.models import (
    Announcement,
    Appointment,
    Consultation,
    Doctor,
    DoctorSchedule,
    InventoryTransaction,
    Medicine,
    Patient,
)


def patients_for(actor) -> QuerySet[Patient]:
    qs = Patient.objects.filter(is_active=True).select_related()
    if actor.has_permission("phc.patient.view"):
        return qs
    return qs.filter(user_id=actor.user_id)


def active_patient_for_user(user_id: int):
    return Patient.objects.filter(user_id=user_id, is_active=True).first()


def appointments_for(actor) -> QuerySet[Appointment]:
    qs = Appointment.objects.select_related("patient", "doctor")
    if actor.has_permission("phc.appointment.view"):
        if actor.has_permission("phc.appointment.view_all"):
            return qs
        doctor = Doctor.objects.filter(user_id=actor.user_id).first()
        if doctor:
            return qs.filter(doctor=doctor)
        return qs
    return qs.filter(patient__user_id=actor.user_id)


def consultations_for(actor):
    qs = Consultation.objects.select_related(
        "appointment__patient", "appointment__doctor"
    ).prefetch_related("prescriptions__items")
    if actor.has_permission("phc.consultation.view_all"):
        return qs
    if actor.has_permission("phc.consultation.view"):
        return qs.filter(appointment__doctor__user_id=actor.user_id)
    return qs.filter(appointment__patient__user_id=actor.user_id)


def medicines() -> QuerySet[Medicine]:
    return Medicine.objects.filter(is_active=True).order_by("name")


def inventory_transactions(medicine_id: int | None = None):
    qs = InventoryTransaction.objects.select_related("medicine").order_by("-created_at")
    return qs.filter(medicine_id=medicine_id) if medicine_id else qs


def announcements(actor) -> QuerySet[Announcement]:
    qs = Announcement.objects.all()
    if not actor.has_permission("phc.announcement.publish"):
        qs = qs.filter(published=True)
    return qs.order_by("-created_at")


def doctors(*, include_unavailable: bool = False) -> QuerySet[Doctor]:
    qs = Doctor.objects.all()
    if not include_unavailable:
        qs = qs.filter(is_available=True)
    return qs.order_by("user_id")


def doctors_for(actor) -> QuerySet[Doctor]:
    include_unavailable = actor.has_permission("phc.appointment.view_all") or (
        actor.has_permission("phc.appointment.manage")
        and not Doctor.objects.filter(user_id=actor.user_id).exists()
    )
    return doctors(include_unavailable=include_unavailable)


def doctor_for(actor, doctor_id: int):
    qs = Doctor.objects.filter(pk=doctor_id)
    if (
        actor.has_permission("phc.appointment.manage")
        and not actor.has_permission("phc.appointment.view_all")
        and Doctor.objects.filter(user_id=actor.user_id).exists()
    ):
        qs = qs.filter(user_id=actor.user_id)
    return qs.first()


def schedules(doctor_id: int | None = None):
    qs = DoctorSchedule.objects.filter(is_active=True).select_related("doctor")
    return qs.filter(doctor_id=doctor_id) if doctor_id else qs
