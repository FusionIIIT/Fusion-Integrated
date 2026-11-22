from django.db import models


class WorkRequest(models.Model):
    """Represents a maintenance or construction work request raised in IWD."""

    CATEGORY_CHOICES = [
        ("civil", "Civil"),
        ("electrical", "Electrical"),
        ("plumbing", "Plumbing"),
        ("carpentry", "Carpentry"),
        ("housekeeping", "Housekeeping"),
        ("repair", "Repair"),
        ("new_construction", "New Construction"),
        ("other", "Other"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("medium", "Medium"),
        ("high", "High"),
        ("urgent", "Urgent"),
    ]

    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
        ("closed", "Closed"),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    location = models.CharField(max_length=300)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES, default="repair")
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default="medium")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    requester_username = models.CharField(max_length=150)
    assigned_to = models.CharField(max_length=150, blank=True, default="")

    estimated_cost = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    actual_cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    required_by = models.DateField(null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    remarks = models.TextField(blank=True, default="")

    class Meta:
        db_table = "iwd_work_request"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"WR-{self.pk}: {self.title} [{self.status}]"


class Contractor(models.Model):
    """Registered contractor who can be assigned work by IWD."""

    name = models.CharField(max_length=200)
    registration_number = models.CharField(max_length=100, unique=True)
    contact_person = models.CharField(max_length=150)
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    specialization = models.CharField(max_length=200, blank=True, default="")
    is_active = models.BooleanField(default=True)
    registered_on = models.DateField(auto_now_add=True)

    class Meta:
        db_table = "iwd_contractor"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.registration_number})"


class InventoryItem(models.Model):
    """Material or equipment tracked in the IWD inventory."""

    name = models.CharField(max_length=200)
    unit = models.CharField(max_length=50)
    quantity_available = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    minimum_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_restocked = models.DateField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_inventory_item"
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.name} ({self.quantity_available} {self.unit})"

    @property
    def is_low_stock(self) -> bool:
        return self.quantity_available <= self.minimum_stock


class WorkRequestLog(models.Model):
    """Audit trail for every status change on a work request."""

    work_request = models.ForeignKey(
        WorkRequest, on_delete=models.CASCADE, related_name="logs"
    )
    from_status = models.CharField(max_length=20, blank=True, default="")
    to_status = models.CharField(max_length=20)
    actor_username = models.CharField(max_length=150)
    note = models.TextField(blank=True, default="")
    changed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iwd_work_request_log"
        ordering = ["changed_at"]

    def __str__(self) -> str:
        return f"WR-{self.work_request_id}: {self.from_status} -> {self.to_status}"

