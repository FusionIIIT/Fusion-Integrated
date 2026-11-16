from django.db import models

from core.db.mixins import TimeStampedModel


class IwdComplaint(TimeStampedModel):
    STATES = [
        ("submitted", "Submitted"),
        ("assigned", "Assigned"),
        ("assessed", "Assessed"),
        ("low_cost_review", "Low-cost review"),
        ("committee_review", "Committee review"),
        ("department_head_review", "Department Head review"),
        ("director_review", "Director review"),
        ("estimate_approved", "Estimate approved"),
        ("bidding_authorized", "Bidding authorized"),
        ("vendor_selected", "Vendor selected"),
        ("materials_pending", "Materials pending"),
        ("materials_available", "Materials available"),
        ("materials_issued", "Materials issued"),
        ("in_progress", "In progress"),
        ("verification_pending", "Verification pending"),
        ("rework_required", "Rework required"),
        ("resolved", "Resolved"),
        ("audit_pending", "Audit pending"),
        ("payment_approval_pending", "Payment approval pending"),
        ("settlement_pending", "Settlement pending"),
        ("settled", "Settled"),
        ("rejected", "Rejected"),
    ]

    reporter_user_id = models.IntegerField(db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    issue_category = models.CharField(max_length=32, default="other")
    location = models.CharField(max_length=200)
    urgency = models.CharField(max_length=16, default="normal")
    remarks = models.TextField(blank=True)
    state = models.CharField(max_length=40, choices=STATES, default="submitted", db_index=True)
    engineer_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    urgent = models.BooleanField(default=False)
    urgent_remarks = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    metadata = models.JSONField(default=dict, blank=True)


class IwdEstimate(TimeStampedModel):
    complaint = models.OneToOneField(
        IwdComplaint, on_delete=models.CASCADE, related_name="estimate"
    )
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    cost_band = models.CharField(max_length=8)
    status = models.CharField(max_length=24, default="submitted")
    estimated_time = models.CharField(max_length=120, blank=True)
    materials = models.JSONField(default=list, blank=True)
    details = models.JSONField(default=dict, blank=True)
    committee_outcome = models.TextField(blank=True)
    decision_reason = models.TextField(blank=True)
    submitted_by_user_id = models.IntegerField()


class IwdInventoryItem(TimeStampedModel):
    name = models.CharField(max_length=160)
    sku = models.CharField(max_length=80, unique=True)
    quantity = models.DecimalField(max_digits=14, decimal_places=3, default=0)
    unit = models.CharField(max_length=32, default="unit")
    active = models.BooleanField(default=True)


class IwdInventoryMovement(TimeStampedModel):
    item = models.ForeignKey(IwdInventoryItem, on_delete=models.PROTECT, related_name="movements")
    complaint = models.ForeignKey(
        IwdComplaint,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="inventory_movements",
    )
    actor_user_id = models.IntegerField()
    quantity = models.DecimalField(max_digits=14, decimal_places=3)
    movement_type = models.CharField(max_length=24)
    remarks = models.TextField(blank=True)


class IwdProcurementNeed(TimeStampedModel):
    STATES = [
        ("pending", "Pending"),
        ("coordinating", "Coordinating"),
        ("completed", "Completed"),
        ("unresolved", "Unresolved"),
    ]

    complaint = models.ForeignKey(
        IwdComplaint, on_delete=models.CASCADE, related_name="procurement_needs"
    )
    actor_user_id = models.IntegerField()
    materials = models.JSONField(default=list)
    route = models.CharField(max_length=32)
    state = models.CharField(max_length=16, choices=STATES, default="pending")
    remarks = models.TextField(blank=True)


class IwdWorkVerification(TimeStampedModel):
    complaint = models.OneToOneField(
        IwdComplaint, on_delete=models.CASCADE, related_name="verification"
    )
    actor_user_id = models.IntegerField()
    outcome = models.CharField(max_length=24)
    remarks = models.TextField(blank=True)
    rework_count = models.PositiveSmallIntegerField(default=0)


class IwdFinalBill(TimeStampedModel):
    STATES = [
        ("audit_pending", "Audit pending"),
        ("queried", "Queried"),
        ("validated", "Validated"),
        ("payment_approval_pending", "Payment approval pending"),
        ("withheld", "Payment withheld"),
        ("settlement_pending", "Settlement pending"),
        ("settled", "Settled"),
    ]

    complaint = models.OneToOneField(
        IwdComplaint, on_delete=models.CASCADE, related_name="final_bill"
    )
    submitted_by_user_id = models.IntegerField()
    invoice_number = models.CharField(max_length=120)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    supporting_records = models.JSONField(default=dict, blank=True)
    audit_remarks = models.TextField(blank=True)
    decision_reason = models.TextField(blank=True)
    settlement_status = models.CharField(max_length=24, blank=True)
    state = models.CharField(max_length=32, choices=STATES, default="audit_pending")


class IwdFeedback(TimeStampedModel):
    complaint = models.ForeignKey(IwdComplaint, on_delete=models.CASCADE, related_name="feedback")
    actor_user_id = models.IntegerField()
    rating = models.PositiveSmallIntegerField(null=True, blank=True)
    comments = models.TextField(blank=True)
    post_repair_issue = models.TextField(blank=True)


class IwdNotification(TimeStampedModel):
    recipient_user_id = models.IntegerField(db_index=True)
    complaint = models.ForeignKey(
        IwdComplaint, on_delete=models.CASCADE, null=True, blank=True, related_name="notifications"
    )
    event = models.CharField(max_length=48)
    message = models.TextField()
    read_at = models.DateTimeField(null=True, blank=True)


class IwdAuditEvent(TimeStampedModel):
    complaint = models.ForeignKey(
        IwdComplaint, on_delete=models.CASCADE, related_name="audit_events"
    )
    actor_user_id = models.IntegerField()
    action = models.CharField(max_length=80)
    from_state = models.CharField(max_length=40, blank=True)
    to_state = models.CharField(max_length=40, blank=True)
    reason = models.TextField(blank=True)
