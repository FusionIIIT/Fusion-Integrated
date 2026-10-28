"""
Leave Ledger Models - Tracks annual leave balances and transactional audit trail.

STAGE 2: DATABASE MODELS & MIGRATIONS
"""

from decimal import Decimal
from django.db import models
from django.db.models import Sum

# ... existing mixins imports from core.db.mixins ...

from core.db.mixins import TimeStampedModel, UserScopedModel


class LeaveBalanceLedger(UserScopedModel, TimeStampedModel):
    """
    Tracks annual leave balance per user, per category, per year.
    Inherits UserScopedModel and TimeStampedModel for identity and audit.
    """
    
    year = models.PositiveIntegerField()
    category = models.CharField(max_length=2, choices=[
        ('cl', 'Casual Leave'),
        ('rh', 'Half Leave'),
        ('scl', 'Sick Leave'),
        ('el', 'Earned Leave'),
        ('vl', 'Vacation Leave'),
        ('col', 'Compensatory Leave'),
    ])
    balance = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    utilized = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=3, decimal_places=2, default=0)
    
    class Meta:
        unique_together = ['user_id', 'year', 'category']
        ordering = ['year', 'category']
    
    def __str__(self):
        return f"{self.user_id} - {self.year} - {self.category} - {self.balance} remaining"
    
    @property
    def remaining(self) -> Decimal:
        """Balance after utilization."""
        return self.balance - self.utilized


class LeaveLedgerTransaction(UserScopedModel, TimeStampedModel):
    """
    Append-only audit log of all balance changes.
    Every modification to LeaveBalanceLedger creates a corresponding transaction.
    """
    
    category = models.CharField(max_length=2, choices=[
        ('cl', 'Casual Leave'),
        ('rh', 'Half Leave'),
        ('scl', 'Sick Leave'),
        ('el', 'Earned Leave'),
        ('vl', 'Vacation Leave'),
        ('col', 'Compensatory Leave'),
    ])
    delta = models.DecimalField(max_digits=3, decimal_places=2)
    transaction_type = models.CharField(
        max_length=20,
        choices=[
            ('credit', 'Credit - Initial Allocation'),
            ('deduction', 'Deduction - Leave Used'),
            ('reversal', 'Reversal - Cancelled/Withdrawn'),
            ('vl_conversion', 'Conversion - VL to EL'),
            ('resumption_adj', 'Adjustment - Early/Late Resumption'),
        ]
    )
    reference_id = models.CharField(max_length=100, blank=True, help_text="Associated request ID or transaction reference")
    remarks = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
           
            models.Index(fields=['user_id', 'transaction_type']),
        ]
    
    def __str__(self):
        return f"{self.user_id} - {self.created_at} - {self.transaction_type} - {self.delta}"