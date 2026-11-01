from datetime import date, datetime, time

from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)
from fusion_auth.client import IamUnavailable
from modules.directory.contracts import get_active_users
from modules.phc.domain.appointments import validate_transition
from modules.phc.models import (
    Announcement,
    Appointment,
    AppointmentTransition,
    Consultation,
    Doctor,
    DoctorSchedule,
    InventoryTransaction,
    Medicine,
    Patient,
    PrescribedMedicine,
    Prescription,
)


def register_patient(*, user_id: int, actor) -> Patient:
    if user_id != actor.user_id and not actor.has_permission("phc.patient.register"):
        raise NotFoundError("Patient not found.", code="not_found")
    try:
        found = get_active_users([user_id])
    except IamUnavailable as exc:
        raise ServiceUnavailableError(
            "The institute directory is temporarily unavailable."
        ) from exc
    if user_id not in found or found[user_id].kind not in {"student", "faculty", "staff"}:
        raise BadRequestError(
            "Select an active student, faculty member or employee.", code="invalid_patient"
        )
    try:
        with transaction.atomic():
            return Patient.objects.create(
                user_id=user_id, patient_number=f"PHC-{user_id:08d}", registered_by=actor.user_id
            )
    except IntegrityError as exc:
        raise ConflictError(
            "This institute user is already registered as a patient.", code="patient_exists"
        ) from exc


def create_doctor(*, user_id: int, specialty: str = "") -> Doctor:
    try:
        found = get_active_users([user_id])
    except IamUnavailable as exc:
        raise ServiceUnavailableError(
            "The institute directory is temporarily unavailable."
        ) from exc
    if user_id not in found or found[user_id].kind not in {"faculty", "staff"}:
        raise BadRequestError(
            "Doctor must be an active faculty or staff account.", code="invalid_doctor"
        )
    with transaction.atomic():
        return Doctor.objects.create(user_id=user_id, specialty=specialty)


def update_doctor(*, doctor_id: int, changes: dict) -> Doctor:
    with transaction.atomic():
        try:
            doctor = Doctor.objects.select_for_update().get(pk=doctor_id)
        except Doctor.DoesNotExist as exc:
            raise NotFoundError("Doctor not found.", code="not_found") from exc
        for key, value in changes.items():
            setattr(doctor, key, value)
        if changes:
            doctor.save(update_fields=[*changes, "updated_at"])
        return doctor


def add_medicine(*, values: dict) -> Medicine:
    try:
        with transaction.atomic():
            return Medicine.objects.create(**values)
    except IntegrityError as exc:
        raise ConflictError(
            "A medicine with that name already exists.", code="medicine_exists"
        ) from exc


def set_schedule(
    *,
    doctor_id: int,
    weekday: int,
    starts_at: time,
    ends_at: time,
    slot_minutes: int,
    effective_from: date,
    effective_until: date | None,
):
    duration = (ends_at.hour * 60 + ends_at.minute) - (starts_at.hour * 60 + starts_at.minute)
    if weekday not in range(7) or duration <= 0 or slot_minutes < 5 or slot_minutes > duration:
        raise BadRequestError(
            "Schedule day, time range or slot length is invalid.", code="invalid_schedule"
        )
    if effective_until and effective_until < effective_from:
        raise BadRequestError("Schedule end date precedes its start date.", code="invalid_schedule")
    with transaction.atomic():
        try:
            Doctor.objects.select_for_update().get(pk=doctor_id)
        except Doctor.DoesNotExist as exc:
            raise NotFoundError("Doctor not found.", code="not_found") from exc
        schedules = DoctorSchedule.objects.filter(
            doctor_id=doctor_id, weekday=weekday, is_active=True
        )
        if effective_until is not None:
            schedules = schedules.filter(effective_from__lte=effective_until)
        schedules = schedules.filter(
            Q(effective_until__isnull=True) | Q(effective_until__gte=effective_from)
        )
        if schedules.filter(starts_at__lt=ends_at, ends_at__gt=starts_at).exists():
            raise ConflictError(
                "Schedule overlaps another active doctor schedule.", code="schedule_conflict"
            )
        return DoctorSchedule.objects.create(
            doctor_id=doctor_id,
            weekday=weekday,
            starts_at=starts_at,
            ends_at=ends_at,
            slot_minutes=slot_minutes,
            effective_from=effective_from,
            effective_until=effective_until,
        )


def book_appointment(
    *, patient_id: int, doctor_id: int, actor_user_id: int, starts_at: datetime, reason: str = ""
) -> Appointment:
    if timezone.is_naive(starts_at):
        starts_at = timezone.make_aware(starts_at, timezone.get_current_timezone())
    if starts_at <= timezone.now():
        raise BadRequestError("Appointments must be booked in the future.", code="past_appointment")
    try:
        with transaction.atomic():
            doctor = (
                Doctor.objects.select_for_update().filter(pk=doctor_id, is_available=True).first()
            )
            if doctor is None:
                raise NotFoundError("Available doctor not found.", code="doctor_unavailable")
            local = timezone.localtime(starts_at)
            schedules = DoctorSchedule.objects.filter(
                doctor=doctor,
                weekday=local.weekday(),
                is_active=True,
                effective_from__lte=local.date(),
            ).filter(Q(effective_until__isnull=True) | Q(effective_until__gte=local.date()))
            clock = local.time().replace(tzinfo=None)
            if not any(
                s.starts_at <= clock < s.ends_at
                and (
                    (clock.hour * 60 + clock.minute - s.starts_at.hour * 60 - s.starts_at.minute)
                    % s.slot_minutes
                    == 0
                )
                for s in schedules
            ):
                raise ConflictError(
                    "Doctor has no schedule at the requested time.", code="slot_unavailable"
                )
            appointment = Appointment.objects.create(
                patient_id=patient_id, doctor=doctor, starts_at=starts_at, reason=reason
            )
            AppointmentTransition.objects.create(
                appointment=appointment,
                from_status="",
                to_status="pending",
                actor_user_id=actor_user_id,
                reason="Appointment requested",
            )
            return appointment
    except IntegrityError as exc:
        raise ConflictError(
            "That doctor and time slot is already booked.", code="slot_booked"
        ) from exc


def transition_appointment(*, appointment_id: int, target: str, actor, reason: str = ""):
    with transaction.atomic():
        try:
            appt = Appointment.objects.select_for_update().get(pk=appointment_id)
        except Appointment.DoesNotExist as exc:
            raise NotFoundError("Appointment not found.", code="not_found") from exc
        try:
            validate_transition(appt.status, target)
        except (ValueError, KeyError) as exc:
            raise ConflictError(str(exc), code="invalid_transition") from exc
        old = appt.status
        appt.status = target
        appt.save(update_fields=["status", "updated_at"])
        AppointmentTransition.objects.create(
            appointment=appt,
            from_status=old,
            to_status=target,
            actor_user_id=actor.user_id,
            reason=reason,
        )
        return appt


def record_consultation(
    *,
    appointment_id: int,
    actor,
    symptoms: str,
    observations: str,
    diagnosis: str,
    treatment: str,
    medicines: list[dict],
):
    with transaction.atomic():
        try:
            appt = Appointment.objects.select_for_update().get(pk=appointment_id)
        except Appointment.DoesNotExist as exc:
            raise NotFoundError("Appointment not found.", code="not_found") from exc
        if appt.status not in {"confirmed", "completed"}:
            raise ConflictError(
                "Only confirmed appointments can be consulted.", code="appointment_not_ready"
            )
        if appt.doctor.user_id != actor.user_id:
            raise NotFoundError("Appointment not found.", code="not_found")
        if hasattr(appt, "consultation"):
            raise ConflictError(
                "Consultation already exists and is immutable.", code="consultation_exists"
            )
        consult = Consultation.objects.create(
            appointment=appt,
            recorded_by=actor.user_id,
            symptoms=symptoms,
            observations=observations,
            diagnosis=diagnosis,
            treatment=treatment,
            finalized_at=timezone.now(),
        )
        if medicines:
            prescription = Prescription.objects.create(
                consultation=consult, issued_by=actor.user_id
            )
            PrescribedMedicine.objects.bulk_create(
                [PrescribedMedicine(prescription=prescription, **item) for item in medicines]
            )
        if appt.status == "confirmed":
            transition_appointment(appointment_id=appt.pk, target="completed", actor=actor)
        return consult


def stock(
    *,
    medicine_id: int,
    quantity: int,
    action: str,
    actor,
    patient_id: int | None = None,
    note: str = "",
) -> Medicine:
    if quantity <= 0 or action not in {"addition", "dispense"}:
        raise BadRequestError(
            "Stock operation must have a positive quantity and valid action.",
            code="invalid_stock_operation",
        )
    if (
        patient_id is not None
        and not Patient.objects.filter(user_id=patient_id, is_active=True).exists()
    ):
        raise BadRequestError("Patient does not exist.", code="invalid_patient")
    with transaction.atomic():
        try:
            medicine = Medicine.objects.select_for_update().get(pk=medicine_id, is_active=True)
        except Medicine.DoesNotExist as exc:
            raise NotFoundError("Medicine not found.", code="not_found") from exc
        if action == "dispense":
            if medicine.expires_on and medicine.expires_on < timezone.localdate():
                raise ConflictError(
                    "Expired medicine cannot be dispensed.", code="medicine_expired"
                )
            if medicine.quantity < quantity:
                raise ConflictError("Insufficient medicine stock.", code="insufficient_stock")
            medicine.quantity -= quantity
        else:
            medicine.quantity += quantity
        medicine.save(update_fields=["quantity", "updated_at"])
        InventoryTransaction.objects.create(
            medicine=medicine,
            transaction_type=action,
            quantity=quantity,
            actor_user_id=actor.user_id,
            patient_id=patient_id,
            note=note,
        )
        return medicine


def publish_announcement(*, title: str, body: str, actor) -> Announcement:
    return Announcement.objects.create(title=title, body=body, created_by=actor.user_id)
