from django.db import models
from core.db.mixins import TimeStampedModel

class IwdRequest(TimeStampedModel):
    title = models.CharField(max_length=200)
    area = models.CharField(max_length=100, blank=True)
    description = models.TextField()
    priority = models.CharField(max_length=32, choices=[('low', 'low'), ('medium', 'medium'), ('high', 'high')], default='medium')
    creator_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=32, choices=[
        ('pending', 'pending'),
        ('admin_approved', 'admin_approved'),
        ('hod_approved', 'hod_approved'),
        ('approved', 'approved'),
        ('rejected', 'rejected'),
        ('work_in_progress', 'work_in_progress'),
        ('completed', 'completed'),
        ('billing', 'billing'),
        ('settled', 'settled')
    ], default='pending')
    next_approver = models.CharField(max_length=80, blank=True)

    class Meta:
        pass

class RequestTransition(TimeStampedModel):
    request = models.ForeignKey(IwdRequest, on_delete=models.CASCADE, related_name='transitions')
    from_status = models.CharField(max_length=32)
    to_status = models.CharField(max_length=32)
    actor_id = models.IntegerField()
    note = models.TextField(blank=True)

    class Meta:
        unique_together = ('request', 'from_status', 'to_status')

class Proposal(TimeStampedModel):
    request = models.ForeignKey(IwdRequest, on_delete=models.CASCADE, related_name='proposals')
    creator_id = models.IntegerField()
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=32, choices=[('draft', 'draft'), ('submitted', 'submitted'), ('approved', 'approved'), ('rejected', 'rejected')], default='draft')

    class Meta:
        pass

class WorkOrder(TimeStampedModel):
    request = models.OneToOneField(IwdRequest, on_delete=models.CASCADE, related_name='work_order')
    issuer_id = models.IntegerField()
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    start_date = models.DateField(null=True, blank=True)
    completion_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=[('open', 'open'), ('in_progress', 'in_progress'), ('completed', 'completed')], default='open')

    class Meta:
        pass

class Vendor(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='vendors')
    name = models.CharField(max_length=200)
    contact = models.CharField(max_length=32, blank=True)
    email = models.EmailField(blank=True)

    class Meta:
        pass

class Bill(TimeStampedModel):
    work_order = models.ForeignKey(WorkOrder, on_delete=models.CASCADE, related_name='bills')
    vendor = models.ForeignKey(Vendor, null=True, blank=True, on_delete=models.SET_NULL)
    bill_type = models.CharField(max_length=32, choices=[('partial', 'partial'), ('final', 'final')], default='partial')
    amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=32, choices=[('draft', 'draft'), ('pending', 'pending'), ('audited', 'audited'), ('settled', 'settled'), ('rejected', 'rejected')], default='draft')
    created_by = models.IntegerField()

    class Meta:
        pass

class InventoryItem(TimeStampedModel):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=40)
    available_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=0)
    location = models.CharField(max_length=100, blank=True)

    class Meta:
        pass

class Feedback(TimeStampedModel):
    request = models.ForeignKey(IwdRequest, on_delete=models.CASCADE, related_name='feedback')
    submitter_id = models.IntegerField()
    rating = models.PositiveSmallIntegerField()
    comments = models.TextField(blank=True)
    reopened = models.BooleanField(default=False)

    class Meta:
        pass
