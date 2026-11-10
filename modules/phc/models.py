from django.db import models

class AuditEvent(models.Model):
    """Immutable audit trail of successful sensitive actions (PHC-BR-09)."""

    entity_type = models.CharField(max_length=40)
    entity_id = models.IntegerField()
    action = models.CharField(max_length=40)
    from_status = models.CharField(max_length=32, blank=True)
    to_status = models.CharField(max_length=32, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_role = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_audit_event"
        ordering = ["at", "id"]
        indexes = [models.Index(fields=["entity_type", "entity_id", "at"], name="phc_audit_entity_idx")]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise PermissionError("Audit events are immutable")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise PermissionError("Audit events are immutable")

    def __str__(self) -> str:
        return f"{self.entity_type}#{self.entity_id} {self.action}"


class Notification(models.Model):
    """In-app notification to one user (PHC-BR-07, PHC-BR-11, PHC-BR-13)."""

    recipient_user_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=40)
    message = models.CharField(max_length=300)
    entity_type = models.CharField(max_length=40, blank=True)
    entity_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_notification"
        ordering = ["-created_at", "-id"]

    def __str__(self) -> str:
        return f"to u{self.recipient_user_id}: {self.kind}"


class PatientVisit(models.Model):
    """Tracks a patient's clinic visit (PHC-BR-02)."""

    patient_user_id = models.IntegerField(db_index=True)
    visited_on = models.DateField()
    notes = models.TextField(blank=True, null=True)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_patient_visit"
        ordering = ["-visited_on", "-created_at"]

    def __str__(self) -> str:
        return f"Visit by u{self.patient_user_id} on {self.visited_on}"


class Prescription(models.Model):
    """A digitized prescription linked to a PatientVisit (PHC-BR-02, PHC-BR-05)."""

    patient_visit = models.ForeignKey(PatientVisit, related_name="prescriptions", on_delete=models.CASCADE)
    details = models.TextField()
    issued_on = models.DateField()

    class Meta:
        db_table = "phc_prescription"
        ordering = ["-issued_on"]

    def __str__(self) -> str:
        return f"Prescription for visit by u{self.patient_visit.patient_user_id} on {self.issued_on}"


class ReimbursementClaim(models.Model):
    """An employee's medical bill claim (PHC-BR-04, PHC-BR-08)."""

    claimant_user_id = models.IntegerField(db_index=True)
    prescription = models.ForeignKey(Prescription, related_name="claims", on_delete=models.PROTECT)
    expense_date = models.DateField()
    claimed_amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=300, blank=True, null=True)
    status = models.CharField(max_length=40, default="PENDING_PHC_REVIEW")
    submitted_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "phc_reimbursement_claim"
        ordering = ["-submitted_at"]

    def __str__(self) -> str:
        return f"Claim by u{self.claimant_user_id} for prescription on {self.expense_date}"


class ReimbursementPayment(models.Model):
    """Tracks final payment of a claim (PHC-BR-08)."""

    claim = models.OneToOneField(ReimbursementClaim, related_name="payment", on_delete=models.PROTECT)
    paid_on = models.DateField()
    reference = models.CharField(max_length=100)
    recorded_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "phc_reimbursement_payment"
        ordering = ["-paid_on"]

    def __str__(self) -> str:
        return f"Payment for claim by u{self.claim.claimant_user_id} on {self.paid_on}"


class InventoryItem(models.Model):
    """Represents a medicine or consumable in stock (PHC-BR-07)."""

    name = models.CharField(max_length=100)
    unit = models.CharField(max_length=50)
    quantity = models.IntegerField(default=0)
    reorder_threshold = models.IntegerField(default=0)

    class Meta:
        db_table = "phc_inventory_item"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.quantity})"


class StockAdjustment(models.Model):
    """Logs an addition or deduction of stock (PHC-BR-07, PHC-BR-09)."""

    inventory_item = models.ForeignKey(InventoryItem, related_name="adjustments", on_delete=models.CASCADE)
    delta = models.IntegerField()
    reason = models.CharField(max_length=300)
    adjusted_by_user_id = models.IntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "phc_stock_adjustment"
        ordering = ["-at"]

    def __str__(self) -> str:
        return f"Adjustment of {self.inventory_item.name} by u{self.adjusted_by_user_id} on {self.at}"


class Requisition(models.Model):
    """A procurement request created by PHC staff (PHC-BR-10, PHC-BR-11)."""

    requested_by_user_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=40, default="PENDING_APPROVAL")
    created_at = models.DateTimeField(auto_now_add=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "phc_requisition"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Requisition by u{self.requested_by_user_id} on {self.created_at}"


class RequisitionLine(models.Model):
    """Line items inside a requisition (PHC-BR-10, PHC-BR-11)."""

    requisition = models.ForeignKey(Requisition, related_name="lines", on_delete=models.CASCADE)
    inventory_item = models.ForeignKey(InventoryItem, related_name="requisitions", on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField()

    class Meta:
        db_table = "phc_requisition_line"
        ordering = ["-quantity"]

    def __str__(self) -> str:
        return f"Line item for {self.inventory_item.name} in requisition by u{self.requisition.requested_by_user_id}"
