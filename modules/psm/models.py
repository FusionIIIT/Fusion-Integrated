from django.db import models
from core.files.storage import path_for
from core.observability.middleware import get_request_id
from core.db.mixins import UserScopedModel, TimeStampedModel

class StockItem(models.Model):
    id = models.AutoField(primary_key=True)
    item_code = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    unit = models.CharField(max_length=20)
    available_quantity = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

class PurchaseIndent(UserScopedModel):
    id = models.AutoField(primary_key=True)
    indent_number = models.CharField(max_length=50, unique=True)
    title = models.CharField(max_length=255)
    department = models.CharField(max_length=100)
    justification = models.TextField()
    total_estimated_cost = models.DecimalField(max_digits=10, decimal_places=2)
    priority = models.CharField(max_length=20, choices=[('low', 'Low'), ('normal', 'Normal'), ('high', 'High'), ('urgent', 'Urgent')])
    status = models.CharField(max_length=20, choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('cancelled', 'Cancelled')])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

class IndentItem(models.Model):
    id = models.AutoField(primary_key=True)
    indent = models.ForeignKey(PurchaseIndent, on_delete=models.CASCADE)
    item_name = models.CharField(max_length=100)
    quantity = models.IntegerField()
    unit = models.CharField(max_length=20)
    estimated_unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    specifications = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.item_name
