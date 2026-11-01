from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel

class MonthlyBill(TimeStampedModel, UserScopedModel):
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    served_days = models.PositiveSmallIntegerField()
    daily_rate = models.DecimalField(max_digits=7, decimal_places=2)
    special_food_charges = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    rebate_deduction = models.DecimalField(max_digits=9, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    STATUS = [
        ("GENERATED", "Generated"),
        ("FINALIZED", "Finalized"),
        ("PUBLISHED", "Published"),
    ]
    
    status = models.CharField(max_length=10, choices=STATUS, default="GENERATED")
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        db_table = "mess_monthly_bill"
        constraints = [
            models.UniqueConstraint(fields=['user_id', 'year', 'month'], name='unique_user_year_month')
        ]
    
    def __str__(self):
        return f"MonthlyBill: {self.year}-{self.month}"
