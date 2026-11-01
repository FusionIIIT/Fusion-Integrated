"""PHC domain models — one row per persisted requirement artefact.

No cross-module ForeignKeys: `user_id` is the IAM id kept unconstrained so the
module can be extracted without schema surgery. Every writeable row records the
actor who caused it so the audit trail (AFR-PHC-037) can append an entry.
"""
from django.db import models

from core.db.mixins import TimeStampedModel, UserScopedModel


class DoctorSchedule(TimeStampedModel):
    """The master weekly schedule of visiting doctors (AFR-PHC-002 / -004)."""

    doctor_name = models.CharField(max_length=120, db_index=True)
    day_of_week = models.PositiveSmallIntegerField(  # 0=Mon … 6=Sun
        db_index=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    is_published = models.BooleanField(default=False)  # AFR-PHC-005
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)  # IAM id

    class Meta:
        db_table = "phc_doctor_schedule"
        indexes = [
            models.Index(fields=["doctor_name", "day_of_week"],
                         name="phc_sched_doctor_day_idx"),
        ]
        ordering = ["doctor_name", "day_of_week", "start_time"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor_name", "day_of_week"],
                name="phc_one_schedule_per_doctor_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_name} [{self.get_day_of_week_display()}]"


class DoctorAttendance(TimeStampedModel):
    """Real-time Available / Departed status per doctor per day (AFR-PHC-003)."""

    STATUS = [("available", "Available"), ("departed", "Departed")]

    doctor_name = models.CharField(max_length=120, db_index=True)
    date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=STATUS, default="available")
    updated_by = models.IntegerField(null=True, blank=True)  # IAM id

    class Meta:
        db_table = "phc_doctor_attendance"
        ordering = ["-date", "doctor_name"]
        constraints = [
            models.UniqueConstraint(
                fields=["doctor_name", "date"],
                name="phc_one_attendance_per_doctor_day",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.doctor_name} {self.date} {self.status}"


class Patient(TimeStampedModel, UserScopedModel):
    """A patient profile projected from IAM (AFR-PHC-006)."""

    user_id = models.IntegerField(primary_key=True)  # IAM's id
    display_name = models.CharField(max_length=150)
    kind = models.CharField(max_length=16, db_index=True)  # student | employee

    class Meta:
        db_table = "phc_patient"

    def __str__(self) -> str:
        return f"{self.display_name} <{self.user_id}>"


class Visit(TimeStampedModel, UserScopedModel):
    """A patient consultation record (AFR-PHC-007)."""

    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,
                                related_name="visits")
    recorded_by = models.IntegerField(null=True, blank=True)  # PHC Staff id
    notes = models.TextField(blank=True)
    visit_date = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_visit"
        ordering = ["-visit_date"]

    def __str__(self) -> str:
        return f"visit {self.pk} for patient {self.patient_id}"


class Prescription(TimeStampedModel, UserScopedModel):
    """A digitized prescription linked to a patient/visit (AFR-PHC-008)."""

    visit = models.ForeignKey(Visit, on_delete=models.CASCADE,
                              related_name="prescriptions")
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE,
                                related_name="prescriptions")
    medicine = models.CharField(max_length=200)
    dosage = models.CharField(max_length=120, blank=True)
    recorded_by = models.IntegerField(null=True, blank=True)  # PHC Staff id

    class Meta:
        db_table = "phc_prescription"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"prescription {self.pk} for patient {self.patient_id}"


class ReimbursementClaim(TimeStampedModel, UserScopedModel):
    """A medical bill reimbursement claim progressing through fixed stages.

    Forward-only lifecycle per AFR-PHC-017 / AFR-PHC-038: submission is the
    only entry, rejection at sanction is terminal, and any later application is
    a fresh claim — never an edit or reopen.
    """
    STATE = [
        ("submitted", "Submitted / Pending PHC Review"),
        ("pending_audit", "Pending Accounts & Audit Verification"),
        ("pending_sanction", "Pending Sanction"),
        ("approved_for_payment", "Approved for Payment"),
        ("reimbursed", "Reimbursed"),
        ("rejected", "Rejected"),
    ]

    claim_id = models.AutoField(primary_key=True)
    employee = models.ForeignKey(Patient, on_delete=models.CASCADE,
                                 related_name="claims")
    prescription = models.ForeignKey(Prescription, on_delete=models.PROTECT,
                                     related_name="claims")
    expense_date = models.DateField(db_index=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)

    state = models.CharField(max_length=24, choices=STATE, default="submitted",
                             db_index=True)
    stage_actor = models.CharField(max_length=40, blank=True)  # role owning it
    action_history = models.JSONField(default=list, blank=True)  # list[str]

    class Meta:
        db_table = "phc_reimbursement_claim"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["employee", "state"],
                         name="phc_claim_employee_state_idx"),
        ]

    def __str__(self) -> str:
        return f"claim {self.claim_id} ({self.state})"


class InventoryItem(TimeStampedModel):
    """A stocked item with a reorder threshold (AFR-PHC-024 .. -026)."""

    name = models.CharField(max_length=120, db_index=True)
    unit = models.CharField(max_length=40, default="units")
    quantity = models.IntegerField(default=0)  # current stock level
    reorder_threshold = models.IntegerField(default=0)

    class Meta:
        db_table = "phc_inventory_item"
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class StockAdjustment(TimeStampedModel, UserScopedModel):
    """An add / deduct to stock; triggers the threshold check (AFR-PHC-024)."""

    DIRECTION = [("add", "Add"), ("deduct", "Deduct")]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE,
                             related_name="adjustments")
    quantity = models.IntegerField()  # absolute amount changed
    direction = models.CharField(max_length=8, choices=DIRECTION)
    adjusted_by = models.IntegerField(null=True, blank=True)  # PHC Staff id
    reason = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "phc_stock_adjustment"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.direction} {self.quantity} x {self.item_id}"


class Requisition(TimeStampedModel, UserScopedModel):
    """An inventory procurement requisition routed to the Approving Authority.

    States: Pending Approval -> Approved / Rejected -> Fulfilled.
    Fulfillment never auto-posts stock (AFR-PHC-031 note).
    """
    STATE = [
        ("pending_approval", "Pending Approval"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("fulfilled", "Fulfilled"),
    ]

    requisition_id = models.AutoField(primary_key=True)
    originator = models.ForeignKey(Patient, on_delete=models.CASCADE,
                                   related_name="requisitions")
    decided_by = models.IntegerField(null=True, blank=True)  # Approving Authority
    decided_at = models.DateTimeField(null=True, blank=True)
    state = models.CharField(max_length=20, choices=STATE,
                             default="pending_approval", db_index=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "phc_requisition"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"requisition {self.requisition_id} ({self.state})"


class RequisitionItem(TimeStampedModel):
    """Line items inside a requisition (AFR-PHC-027)."""

    requisition = models.ForeignKey(Requisition, on_delete=models.CASCADE,
                                    related_name="lines")
    item = models.ForeignKey(InventoryItem, on_delete=models.PROTECT,
                             related_name="requisition_lines")
    quantity = models.IntegerField()

    class Meta:
        db_table = "phc_requisition_item"

    def __str__(self) -> str:
        return f"{self.quantity} x {self.item_id} -> {self.requisition_id}"


class AmbulanceLog(TimeStampedModel, UserScopedModel):
    """Ambulance usage record: timestamp, patient name, destination (AFR-PHC-032)."""

    timestamp = models.DateTimeField(db_index=True)
    patient_name = models.CharField(max_length=120)
    destination = models.CharField(max_length=200)
    logged_by = models.IntegerField(null=True, blank=True)  # PHC Staff id

    class Meta:
        db_table = "phc_ambulance_log"
        ordering = ["-timestamp"]

    def __str__(self) -> str:
        return f"ambulance {self.pk} at {self.timestamp}"


class HealthAdvisory(TimeStampedModel, UserScopedModel):
    """A health advisory visible to all patients (AFR-PHC-033)."""

    title = models.CharField(max_length=160)
    content = models.TextField()
    is_published = models.BooleanField(default=False)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)  # PHC Staff id

    class Meta:
        db_table = "phc_health_advisory"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return self.title


class AuditLog(TimeStampedModel):
    """Immutable append-only trail for sensitive patient / inventory / claim
    changes (AFR-PHC-037). Never updated or deleted after creation.
    """

    actor = models.IntegerField(null=True, blank=True)  # IAM id who acted
    actor_role = models.CharField(max_length=40, blank=True)
    action = models.CharField(max_length=80)  # e.g. "claim.submitted"
    target_type = models.CharField(max_length=40)  # claim | inventory | visit
    target_id = models.IntegerField(db_index=True)
    detail = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "phc_audit_log"
        ordering = ["-created_at"]
        get_latest_by = "created_at"

    def __str__(self) -> str:
        return f"{self.action} {self.target_type}#{self.target_id}"
