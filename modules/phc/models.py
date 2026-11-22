from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel

APPOINTMENT_STATUSES = ("pending", "confirmed", "completed", "cancelled", "rejected", "no_show")


class Patient(TimeStampedModel):
    """Institute identity reference; the IAM remains the identity source."""

    user_id = models.IntegerField(unique=True)
    patient_number = models.CharField(max_length=24, unique=True)
    registered_by = models.IntegerField()
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_patient"
        indexes = [
            models.Index(fields=["is_active", "patient_number"], name="phc_patient_active_idx")
        ]


class Doctor(TimeStampedModel):
    user_id = models.IntegerField(unique=True)
    specialty = models.CharField(max_length=100, blank=True)
    is_available = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_doctor"


class DoctorSchedule(TimeStampedModel):
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="schedules")
    weekday = models.PositiveSmallIntegerField()
    starts_at = models.TimeField()
    ends_at = models.TimeField()
    slot_minutes = models.PositiveSmallIntegerField(default=15)
    effective_from = models.DateField()
    effective_until = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_doctor_schedule"
        constraints = [
            models.CheckConstraint(condition=Q(weekday__lte=6), name="phc_schedule_weekday_valid"),
            models.CheckConstraint(
                condition=Q(ends_at__gt=models.F("starts_at")), name="phc_schedule_time_valid"
            ),
            models.CheckConstraint(
                condition=Q(effective_until__isnull=True)
                | Q(effective_until__gte=models.F("effective_from")),
                name="phc_schedule_dates_valid",
            ),
            models.CheckConstraint(
                condition=Q(slot_minutes__gte=5), name="phc_schedule_slot_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["doctor", "weekday", "is_active"], name="phc_schedule_lookup_idx")
        ]


class Appointment(TimeStampedModel):
    STATUS = [(s, s.replace("_", " ").title()) for s in APPOINTMENT_STATUSES]
    patient = models.ForeignKey(Patient, on_delete=models.PROTECT, related_name="appointments")
    doctor = models.ForeignKey(Doctor, on_delete=models.PROTECT, related_name="appointments")
    starts_at = models.DateTimeField()
    status = models.CharField(max_length=16, choices=STATUS, default="pending")
    reason = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "phc_appointment"
        constraints = [
            models.UniqueConstraint(
                fields=["doctor", "starts_at"],
                condition=Q(status__in=("pending", "confirmed")),
                name="phc_doctor_slot_unique",
            ),
            models.CheckConstraint(
                condition=Q(status__in=APPOINTMENT_STATUSES), name="phc_appointment_status_valid"
            ),
        ]
        indexes = [
            models.Index(fields=["patient", "-starts_at"], name="phc_appt_patient_idx"),
            models.Index(fields=["doctor", "starts_at"], name="phc_appt_doctor_idx"),
        ]


class AppointmentTransition(TimeStampedModel):
    appointment = models.ForeignKey(
        Appointment, on_delete=models.CASCADE, related_name="transitions"
    )
    from_status = models.CharField(max_length=16)
    to_status = models.CharField(max_length=16)
    actor_user_id = models.IntegerField()
    reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "phc_appointment_transition"


class Consultation(TimeStampedModel):
    appointment = models.OneToOneField(
        Appointment, on_delete=models.PROTECT, related_name="consultation"
    )
    recorded_by = models.IntegerField()
    symptoms = models.TextField(max_length=4000)
    observations = models.TextField(max_length=4000, blank=True)
    diagnosis = models.TextField(max_length=2000)
    treatment = models.TextField(max_length=4000, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_consultation"
        indexes = [models.Index(fields=["-created_at"], name="phc_consult_recent_idx")]


class Prescription(TimeStampedModel):
    consultation = models.ForeignKey(
        Consultation, on_delete=models.PROTECT, related_name="prescriptions"
    )
    issued_by = models.IntegerField()

    class Meta:
        db_table = "phc_prescription"


class PrescribedMedicine(TimeStampedModel):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name="items")
    medicine_name = models.CharField(max_length=150)
    dosage = models.CharField(max_length=100)
    frequency = models.CharField(max_length=100)
    duration = models.CharField(max_length=100)
    instructions = models.CharField(max_length=500, blank=True)

    class Meta:
        db_table = "phc_prescribed_medicine"


class Medicine(TimeStampedModel):
    name = models.CharField(max_length=150, unique=True)
    unit = models.CharField(max_length=40)
    quantity = models.PositiveIntegerField(default=0)
    low_stock_threshold = models.PositiveIntegerField(default=0)
    expires_on = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = "phc_medicine"
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=0), name="phc_medicine_qty_nonnegative"
            )
        ]
        indexes = [models.Index(fields=["quantity", "expires_on"], name="phc_medicine_stock_idx")]


class InventoryTransaction(TimeStampedModel):
    medicine = models.ForeignKey(Medicine, on_delete=models.PROTECT, related_name="transactions")
    transaction_type = models.CharField(
        max_length=12, choices=[("addition", "Addition"), ("dispense", "Dispense")]
    )
    quantity = models.PositiveIntegerField()
    actor_user_id = models.IntegerField()
    patient_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "phc_inventory_transaction"
        constraints = [
            models.CheckConstraint(condition=Q(quantity__gt=0), name="phc_inventory_qty_positive")
        ]
        indexes = [
            models.Index(fields=["medicine", "-created_at"], name="phc_inventory_recent_idx")
        ]


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=160)
    body = models.TextField(max_length=3000)
    published = models.BooleanField(default=True)
    created_by = models.IntegerField()

    class Meta:
        db_table = "phc_announcement"
        indexes = [
            models.Index(fields=["published", "-created_at"], name="phc_announce_recent_idx")
        ]
