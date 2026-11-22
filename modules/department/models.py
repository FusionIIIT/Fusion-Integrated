from django.db import models

class DepartmentAnnouncement(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    author_username = models.CharField(max_length=100)
    author_role = models.CharField(max_length=50)
    target_role = models.CharField(max_length=50, default="ALL")
    target_program = models.CharField(max_length=100, default="ALL")
    target_academic_year = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "department_announcement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.author_role})"

class InventoryItem(models.Model):
    item_name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True, default="")
    available_quantity = models.IntegerField(default=0)
    unit = models.CharField(max_length=50, default="units")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "department_inventory_item"

    def __str__(self):
        return f"{self.item_name} - Qty: {self.available_quantity}"

class StockRequest(models.Model):
    STATUS_CHOICES = (
        ("PENDING_HOD_APPROVAL", "Pending HOD Approval"),
        ("APPROVED_FOR_ISSUANCE", "Approved for Issuance"),
        ("REJECTED", "Rejected"),
        ("ISSUED", "Issued"),
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="stock_requests")
    requester_username = models.CharField(max_length=100)
    requester_role = models.CharField(max_length=50, default="Faculty")
    quantity = models.PositiveIntegerField()
    purpose = models.TextField(blank=True, default="")
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="PENDING_HOD_APPROVAL")
    hod_remarks = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "department_stock_request"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Request #{self.id} for {self.item.item_name} ({self.status})"

class StockMovementLog(models.Model):
    MOVEMENT_TYPES = (
        ("INSERTION", "Stock Insertion"),
        ("ISSUANCE", "Stock Issuance"),
    )
    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="movement_logs")
    stock_request = models.ForeignKey(StockRequest, on_delete=models.SET_NULL, null=True, blank=True)
    movement_type = models.CharField(max_length=20, choices=MOVEMENT_TYPES)
    quantity = models.IntegerField()
    performed_by = models.CharField(max_length=100)
    notes = models.TextField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "department_stock_movement_log"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.movement_type} {self.quantity} by {self.performed_by}"
