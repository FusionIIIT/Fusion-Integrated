"""PHC domain models.

Design conventions (mirrors placement):
  - user_id is a plain integer, never a FK - the IAM owns identity.
  - TimeStampedModel gives created_at / updated_at everywhere.
  - Sensitive data classes covered by PHC-BR-09 (audit): patient records,
    inventory levels, reimbursement claim status.
"""

from __future__ import annotations

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone

from core.db.mixins import TimeStampedModel, UserScopedModel

# ---------------------------------------------------------------------------
# 1. Doctor Schedule & Availability  (AFR-PHC-001 … AFR-PHC-005)
# ---------------------------------------------------------------------------


class DoctorSchedule(TimeStampedModel):
    """Master weekly schedule for a visiting doctor (PHC-UC-07, PHC-UC-22).

    One row per doctor per weekday slot.  'published' makes it visible to
    patients (PHC-BR-01).
    """

    DAYS = [
        ("MON", "Monday"),
        ("TUE", "Tuesday"),
        ("WED", "Wednesday"),
        ("THU", "Thursday"),
        ("FRI", "Friday"),
        ("SAT", "Saturday"),
        ("SUN", "Sunday"),
    ]

    doctor_name = models.CharField(max_length=160)
    specialisation = models.CharField(max_length=120, blank=True)
    day_of_week = models.CharField(max_length=3, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=80, blank=True)
    is_published = models.BooleanField(default=False)
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_doctor_schedule"
        ordering = ["day_of_week", "start_time"]
        indexes = [
            models.Index(fields=["is_published", "day_of_week"], name="phc_schedule_published_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_name} ({self.day_of_week} {self.start_time})"


class DoctorAttendance(TimeStampedModel):
    """Real-time doctor attendance for today (PHC-UC-08, AFR-PHC-004).

    PHC Staff marks a doctor Available or Departed on the day.
    """

    STATUS = [
        ("available", "Available"),
        ("departed", "Departed"),
    ]
    schedule = models.ForeignKey(
        DoctorSchedule, on_delete=models.CASCADE, related_name="attendance_records"
    )
    date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=12, choices=STATUS, default="available")
    marked_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_doctor_attendance"
        # Only one attendance record per schedule per day
        constraints = [
            models.UniqueConstraint(
                fields=["schedule", "date"], name="phc_attendance_schedule_date_uniq"
            ),
        ]
        indexes = [
            models.Index(fields=["date"], name="phc_attendance_date_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.schedule.doctor_name} {self.date} {self.status}"


# ---------------------------------------------------------------------------
# 2. Patient Visit Records & Prescriptions  (AFR-PHC-006 … AFR-PHC-012)
# ---------------------------------------------------------------------------


class PatientVisit(TimeStampedModel, UserScopedModel):
    """A visit record created by PHC Staff for a patient (PHC-UC-06).

    user_id is the patient's IAM user id (ownership; PHC-BR-02).
    Sensitive data: covered by audit trail (PHC-BR-09).
    """

    visit_date = models.DateField()
    chief_complaint = models.TextField()
    diagnosis = models.TextField(blank=True)
    notes = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField()  # PHC Staff

    class Meta:
        db_table = "phc_patient_visit"
        indexes = [
            models.Index(fields=["user_id", "visit_date"], name="phc_visit_patient_date_idx"),
        ]

    def __str__(self) -> str:
        return f"visit#{self.pk} patient={self.user_id} {self.visit_date}"


class Prescription(TimeStampedModel, UserScopedModel):
    """A prescription linked to a patient visit (AFR-PHC-008).

    user_id mirrors the visit's patient ownership.
    """

    visit = models.ForeignKey(PatientVisit, on_delete=models.PROTECT, related_name="prescriptions")
    medicine_name = models.CharField(max_length=160)
    dosage = models.CharField(max_length=120)
    duration_days = models.PositiveSmallIntegerField(null=True, blank=True)
    instructions = models.TextField(blank=True)
    prescribed_by_user_id = models.IntegerField()
    expense_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date of medical expense - used for reimbursement window (PHC-BR-06).",
    )

    class Meta:
        db_table = "phc_prescription"
        indexes = [
            models.Index(fields=["user_id", "visit"], name="phc_prescription_patient_idx"),
        ]

    def __str__(self) -> str:
        return f"rx#{self.pk} {self.medicine_name} patient={self.user_id}"


# ---------------------------------------------------------------------------
# 3. Medical Bill Reimbursement  (AFR-PHC-013 … AFR-PHC-021, AFR-PHC-038)
# ---------------------------------------------------------------------------


class ReimbursementConfig(models.Model):
    """Singleton: PHC Admin-configurable submission window (PHC-BR-06)."""

    submission_window_days = models.PositiveIntegerField(
        default=90,
        help_text="Days from expense date within which a claim must be submitted (0 = unlimited).",
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "phc_reimbursement_config"

    def __str__(self) -> str:
        return f"ReimbursementConfig window={self.submission_window_days}d"

    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)


class ReimbursementClaim(TimeStampedModel, UserScopedModel):
    """A medical-bill reimbursement claim submitted by an employee (PHC-UC-04).

    user_id = claimant's IAM user id.
    Immutable after submission (PHC-BR-14): no field is modified post-submit.
    Rejection is terminal; re-application is a fresh row (PHC-BR-14).
    """

    STATUS = [
        ("pending_phc_review", "Pending PHC Review"),
        ("pending_accounts_verification", "Pending Accounts Verification"),
        ("pending_sanction", "Pending Sanction"),
        ("approved_for_payment", "Approved for Payment"),
        ("reimbursed", "Reimbursed"),
        ("rejected", "Rejected"),
    ]

    prescription = models.ForeignKey(
        Prescription, on_delete=models.PROTECT, related_name="reimbursement_claims"
    )
    amount_claimed = models.DecimalField(
        max_digits=10, decimal_places=2, validators=[MinValueValidator("0.01")]
    )
    description = models.TextField(blank=True)
    status = models.CharField(max_length=36, choices=STATUS, default="pending_phc_review")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_reimbursement_claim"
        indexes = [
            models.Index(fields=["user_id", "status"], name="phc_claim_patient_status_idx"),
            models.Index(fields=["status"], name="phc_claim_status_idx"),
        ]

    def __str__(self) -> str:
        return f"claim#{self.pk} u{self.user_id} {self.status}"


class ReimbursementAudit(models.Model):
    """Immutable audit trail for reimbursement claim status changes (AFR-PHC-037,
    PHC-BR-09).  Rows are never updated or deleted.
    """

    claim = models.ForeignKey(
        ReimbursementClaim, on_delete=models.PROTECT, related_name="audit_entries"
    )
    from_status = models.CharField(max_length=36)
    to_status = models.CharField(max_length=36)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_reimbursement_audit"
        indexes = [
            models.Index(fields=["claim", "at"], name="phc_reimb_audit_idx"),
        ]

    def __str__(self) -> str:
        return f"audit claim#{self.claim_id} {self.from_status}→{self.to_status}"


# ---------------------------------------------------------------------------
# 4. Inventory Management & Procurement  (AFR-PHC-024 … AFR-PHC-031)
# ---------------------------------------------------------------------------


class InventoryItem(TimeStampedModel):
    """A consumable stocked at the PHC (PHC-UC-09, AFR-PHC-024)."""

    name = models.CharField(max_length=160, unique=True)
    unit = models.CharField(max_length=40, blank=True, help_text="e.g. tablets, ml, boxes")
    stock_quantity = models.DecimalField(
        max_digits=12, decimal_places=2, default=0, validators=[MinValueValidator(0)]
    )
    reorder_threshold = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text="Low-stock alert fires when stock < this (PHC-BR-07).",
    )
    description = models.TextField(blank=True)

    class Meta:
        db_table = "phc_inventory_item"
        indexes = [
            models.Index(fields=["name"], name="phc_inventory_name_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.stock_quantity} {self.unit})"

    @property
    def is_low_stock(self) -> bool:
        """PHC-BR-07: strictly below threshold."""
        return self.stock_quantity < self.reorder_threshold


class InventoryAudit(models.Model):
    """Immutable record of every stock-level change (PHC-BR-09, AFR-PHC-037)."""

    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT, related_name="audit_entries")
    delta = models.DecimalField(
        max_digits=12, decimal_places=2, help_text="Positive = add, negative = deduct."
    )
    quantity_before = models.DecimalField(max_digits=12, decimal_places=2)
    quantity_after = models.DecimalField(max_digits=12, decimal_places=2)
    actor_user_id = models.IntegerField()
    notes = models.TextField(blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_inventory_audit"
        indexes = [
            models.Index(fields=["item", "at"], name="phc_inv_audit_idx"),
        ]

    def __str__(self) -> str:
        sign = "+" if self.delta >= 0 else ""
        return f"inv-audit#{self.pk} {self.item.name} {sign}{self.delta}"


class ProcurementRequisition(TimeStampedModel):
    """A procurement requisition submitted by PHC Staff (PHC-UC-10, AFR-PHC-027).

    State machine: pending_approval → approved/rejected; approved → fulfilled.
    """

    STATUS = [
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("fulfilled", "Fulfilled"),
    ]

    title = models.CharField(max_length=200)
    justification = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="pending_approval")
    submitted_by_user_id = models.IntegerField()
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decision_notes = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    fulfilled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_procurement_requisition"
        indexes = [
            models.Index(fields=["status"], name="phc_req_status_idx"),
            models.Index(fields=["submitted_by_user_id"], name="phc_req_submitter_idx"),
        ]

    def __str__(self) -> str:
        return f"req#{self.pk} {self.title[:40]} [{self.status}]"


class RequisitionLineItem(models.Model):
    """One item+quantity in a procurement requisition (AFR-PHC-027)."""

    requisition = models.ForeignKey(
        ProcurementRequisition, on_delete=models.CASCADE, related_name="line_items"
    )
    item_name = models.CharField(max_length=160)
    quantity = models.DecimalField(
        max_digits=12, decimal_places=2, validators=[MinValueValidator("0.01")]
    )
    unit = models.CharField(max_length=40, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        db_table = "phc_requisition_line_item"

    def __str__(self) -> str:
        return f"{self.item_name} x{self.quantity} (req#{self.requisition_id})"


# ---------------------------------------------------------------------------
# 5. Ambulance Logs  (AFR-PHC-032)
# ---------------------------------------------------------------------------


class AmbulanceLog(TimeStampedModel):
    """PHC-UC-11: Record ambulance usage (AFR-PHC-032)."""

    patient_name = models.CharField(max_length=160)
    destination = models.CharField(max_length=255)
    usage_at = models.DateTimeField()
    notes = models.TextField(blank=True)
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "phc_ambulance_log"
        ordering = ["-usage_at"]

    def __str__(self) -> str:
        return f"ambulance {self.usage_at:%Y-%m-%d %H:%M} → {self.destination}"


# ---------------------------------------------------------------------------
# 6. Health Announcements  (AFR-PHC-033)
# ---------------------------------------------------------------------------


class HealthAnnouncement(TimeStampedModel):
    """PHC-UC-12: Health advisory published to all patients (AFR-PHC-033)."""

    title = models.CharField(max_length=255)
    body = models.TextField()
    is_published = models.BooleanField(default=True)
    published_by_user_id = models.IntegerField()
    published_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_health_announcement"
        ordering = ["-published_at"]
        indexes = [
            models.Index(
                fields=["is_published", "published_at"], name="phc_announcement_published_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"announcement#{self.pk} {self.title[:60]}"


# ---------------------------------------------------------------------------
# 7. Notification Outbox  (AFR-PHC-023, AFR-PHC-030, PHC-BR-11, PHC-BR-13)
# ---------------------------------------------------------------------------


class PhcNotification(TimeStampedModel):
    """Out-of-band notification queue for PHC events.

    Delivery is best-effort (console/email backend).  Rows are never deleted;
    delivered ones are marked delivered=True.
    """

    EVENT_TYPES = [
        # Reimbursement (PHC-BR-13)
        ("claim_status_changed", "Claim status changed"),
        # Inventory (PHC-BR-11)
        ("requisition_decided", "Requisition decided"),
        # Inventory low-stock (PHC-BR-07)
        ("low_stock_alert", "Low-stock alert"),
    ]

    recipient_user_id = models.IntegerField(db_index=True)
    event_type = models.CharField(max_length=40, choices=EVENT_TYPES)
    subject = models.CharField(max_length=255)
    body = models.TextField()
    delivered = models.BooleanField(default=False)
    delivered_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    reference_id = models.IntegerField(null=True, blank=True, help_text="PK of the related object.")
    reference_type = models.CharField(max_length=40, blank=True)

    class Meta:
        db_table = "phc_notification"
        indexes = [
            models.Index(fields=["delivered", "created_at"], name="phc_notif_pending_idx"),
            models.Index(fields=["recipient_user_id", "delivered"], name="phc_notif_recipient_idx"),
        ]

    def __str__(self) -> str:
        return (
            f"notif#{self.pk} to={self.recipient_user_id} "
            f"type={self.event_type} delivered={self.delivered}"
        )


# ---------------------------------------------------------------------------
# 8. Sensitive-data Audit Trail — patient records  (PHC-BR-09, AFR-PHC-037)
# ---------------------------------------------------------------------------


class PatientRecordAudit(models.Model):
    """Immutable audit for patient visit / prescription create/modify/delete."""

    ACTION = [
        ("create", "Create"),
        ("modify", "Modify"),
        ("delete", "Delete"),
    ]
    RECORD_TYPE = [
        ("visit", "Patient Visit"),
        ("prescription", "Prescription"),
    ]

    record_type = models.CharField(max_length=20, choices=RECORD_TYPE)
    record_id = models.BigIntegerField()
    patient_user_id = models.IntegerField()
    action = models.CharField(max_length=10, choices=ACTION)
    actor_user_id = models.IntegerField(null=True, blank=True)
    details = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_patient_record_audit"
        indexes = [
            models.Index(fields=["patient_user_id", "at"], name="phc_patient_audit_idx"),
            models.Index(fields=["record_type", "record_id"], name="phc_patient_audit_record_idx"),
        ]

    def __str__(self) -> str:
        return f"audit {self.record_type}#{self.record_id} {self.action} by={self.actor_user_id}"
