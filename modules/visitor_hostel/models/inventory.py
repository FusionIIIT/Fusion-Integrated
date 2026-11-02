from django.db import models

class InventoryItem(models.Model):
    name = models.CharField(max_length=100, unique=True)
    item_code = models.CharField(max_length=30, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    unit = models.CharField(max_length=20, default='Units')
    threshold = models.PositiveIntegerField(default=5)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "vh_inventory_item"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.quantity} {self.unit})"

class InventoryReplenishment(models.Model):
    STATUS_CHOICES = [('Requested', 'Requested'), ('Approved', 'Approved'), 
                      ('Procured', 'Procured'), ('Rejected', 'Rejected')]

    item = models.ForeignKey(InventoryItem, on_delete=models.CASCADE, related_name="replenishments")
    quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Requested')
    requested_by = models.CharField(max_length=100)
    approved_by = models.CharField(max_length=100, blank=True, null=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "vh_inventory_replenishment"
        ordering = ["-requested_at"]

    def __str__(self):
        return f"{self.item.name} +{self.quantity} ({self.status})"
