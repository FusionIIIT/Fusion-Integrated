from django.db import models
from decimal import Decimal
from core.db.mixins import TimeStampedModel


# ----------------------------------------------------------------------
# Approval thresholds (used for business logic, not stored in DB)
# ----------------------------------------------------------------------
BUDGET_THRESHOLD_IWD_ADMIN = Decimal("25000.00")
BUDGET_THRESHOLD_HOD = Decimal("250000.00")


# ----------------------------------------------------------------------
# Request
# ----------------------------------------------------------------------
class Request(TimeStampedModel):
    """
    Main request model for IWD Module.
    Sequential approval chain: IWD Admin → HOD/Dean → Director.
    """
    name = models.CharField(max_length=200)
    description = models.CharField(max_length=1000)
    area = models.CharField(max_length=200)
    created_by_id = models.CharField(max_length=200)  # IAM person ID
    engineer_id = models.CharField(max_length=200, null=True, blank=True)

    # Approval flags
    iwd_admin_approved = models.BooleanField(default=False)
    hod_dean_approved = models.BooleanField(default=False)
    director_approved = models.BooleanField(default=False)

    # Status
    status = models.CharField(max_length=200, default="Pending")

    # Work order & billing flags
    work_order_created = models.BooleanField(default=False)
    work_completed = models.BooleanField(default=False)
    bill_generated = models.BooleanField(default=False)
    bill_processed = models.BooleanField(default=False)
    bill_settled = models.BooleanField(default=False)

    # Proposal
    active_proposal_id = models.IntegerField(null=True, blank=True)

    # Budget & priority
    estimated_budget = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True
    )
    is_priority = models.BooleanField(default=False)

    # SLA deadlines
    iwd_admin_deadline = models.DateTimeField(null=True, blank=True)
    hod_deadline = models.DateTimeField(null=True, blank=True)
    director_deadline = models.DateTimeField(null=True, blank=True)

    # Next approver role
    next_approver = models.CharField(max_length=100, default="IWD Admin")

    def __str__(self):
        return f"Request {self.id}: {self.name}"


# ----------------------------------------------------------------------
# Work Order
# ----------------------------------------------------------------------
class WorkOrder(TimeStampedModel):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="work_orders")
    name = models.CharField(max_length=200)
    estimate_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    allotted_time = models.CharField(max_length=200, blank=True)
    start_date = models.DateField()
    completion_date = models.DateField(null=True, blank=True)
    issuer_id = models.CharField(max_length=200, blank=True)
    amount_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"WorkOrder {self.id} for Request {self.request_id}"


# ----------------------------------------------------------------------
# Vendor
# ----------------------------------------------------------------------
class Vendor(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name="vendors")
    name = models.CharField(max_length=200)
    final_bill = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    contact_number = models.CharField(max_length=20, blank=True, null=True)
    email_address = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self):
        return f"Vendor {self.name} (WorkOrder {self.work_order_id})"


# ----------------------------------------------------------------------
# Bill
# ----------------------------------------------------------------------
class Bill(TimeStampedModel):
    vendor = models.ForeignKey(Vendor, on_delete=models.CASCADE, related_name="bills", null=True, blank=True)
    audit = models.BooleanField(default=False)
    settle = models.BooleanField(default=False)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    BILL_TYPE_CHOICES = [
        (0, "Partial"),
        (1, "Final"),
    ]
    bill_type = models.IntegerField(choices=BILL_TYPE_CHOICES, default=0)

    def __str__(self):
        return f"Bill {self.id} ({self.get_bill_type_display()})"


# ----------------------------------------------------------------------
# Bill Item
# ----------------------------------------------------------------------
class BillItem(TimeStampedModel):
    bill = models.ForeignKey(Bill, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=100, blank=True)
    quantity = models.IntegerField(default=0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} x{self.quantity}"


# ----------------------------------------------------------------------
# Budget
# ----------------------------------------------------------------------
class Budget(TimeStampedModel):
    name = models.CharField(max_length=200)
    issued = models.BooleanField(default=False)

    def __str__(self):
        return f"Budget {self.name}"


# ----------------------------------------------------------------------
# Proposal
# ----------------------------------------------------------------------
class Proposal(TimeStampedModel):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="proposals")
    created_by_id = models.CharField(max_length=200)
    proposal_budget = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)

    STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pending")

    def __str__(self):
        return f"Proposal {self.id} for Request {self.request_id}"


# ----------------------------------------------------------------------
# Proposal Item
# ----------------------------------------------------------------------
class ProposalItem(TimeStampedModel):
    proposal = models.ForeignKey(Proposal, on_delete=models.CASCADE, related_name="items")
    name = models.CharField(max_length=255, default=" ")
    description = models.TextField(default=" ")
    unit = models.CharField(max_length=50, default=" ")
    price_per_unit = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    quantity = models.IntegerField(default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"


# ----------------------------------------------------------------------
# Inventory Item
# ----------------------------------------------------------------------
class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    unit = models.CharField(max_length=50)
    quantity_available = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=10)
    location = models.CharField(max_length=200, blank=True, default="")

    def __str__(self):
        return f"{self.name} ({self.quantity_available} {self.unit})"

    @property
    def is_low_stock(self):
        return self.quantity_available <= self.reorder_level

    @property
    def needs_procurement(self):
        return self.quantity_available <= 0


# ----------------------------------------------------------------------
# Inventory Transaction
# ----------------------------------------------------------------------
class InventoryTransaction(TimeStampedModel):
    TRANSACTION_TYPE_CHOICES = [
        ("issue", "Issue"),
        ("receipt", "Receipt"),
        ("adjustment", "Adjustment"),
    ]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES)
    quantity = models.IntegerField(help_text="Positive for receipt, negative for issue")
    request = models.ForeignKey(Request, on_delete=models.SET_NULL, null=True, blank=True, related_name="inventory_transactions")
    performed_by_id = models.CharField(max_length=200)
    remarks = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.get_transaction_type_display()}: {self.item.name} x{self.quantity}"


# ----------------------------------------------------------------------
# Feedback
# ----------------------------------------------------------------------
class Feedback(TimeStampedModel):
    RATING_CHOICES = [(i, str(i)) for i in range(1, 6)]

    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="feedbacks")
    submitted_by_id = models.CharField(max_length=200)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comments = models.TextField(blank=True, default="")
    reopened = models.BooleanField(default=False)

    def __str__(self):
        return f"Feedback {self.id} for Request {self.request_id}"


# ----------------------------------------------------------------------
# SLA Escalation
# ----------------------------------------------------------------------
class SLAEscalation(TimeStampedModel):
    request = models.ForeignKey(Request, on_delete=models.CASCADE, related_name="escalations")
    escalated_from = models.CharField(max_length=100)
    escalated_to = models.CharField(max_length=100)
    reason = models.TextField()
    resolved = models.BooleanField(default=False)

    def __str__(self):
        return f"Escalation {self.id} for Request {self.request_id}"

