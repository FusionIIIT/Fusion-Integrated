"""Leave domain tables.

Institute people are referenced by plain `user_id` integers, never foreign
keys — there is no user table in this database.
"""

from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


# --- Leave Categories ---
class LeaveCategory(models.Model):
    """Defines supported leave types (CL, RH, SCL, EL, COL, VL)."""
    CODE_CHOICES = [
        ("CL", "Casual Leave"), ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"), ("EL", "Earned Leave"),
        ("COL", "Casual Leave"), ("VL", "Vacation Leave"),
    ]
    code = models.CharField(max_length=3, unique=True)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_carry_forwardable = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_category"
        unique_together = (('code',),)

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


# --- Leave Application ---
class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Represents a single leave request."""
    STATUS_CHOICES = [
        ("draft", "Draft"), ("submitted", "Submitted"),
        ("under_review", "Under Review"), ("shortlisted", "Shortlisted"),
        ("interview_scheduled", "Interview Scheduled"),
        ("selected", "Selected"), ("rejected", "Rejected"), ("withdrawn", "Withdrawn"),
        ("auto_withdrawn", "Withdrawn Automatically"), ("offer_issued", "Offer Issued"),
        ("offer_accepted", "Offer Accepted"), ("offer_declined", "Offer Declined"),
        ("offer_expired", "Offer Expired"),
    ]

    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="applications")
    
    # Leave details
    start_date = models.DateField()
    end_date = models.DateField()
    
    # Half-day CL support (0.5 day)
    is_half_day = models.BooleanField(default=False)
    
    # Station Leave details (captured inside the same application)
    is_station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(default=dict, blank=True)
    
    # Application metadata
    reason = models.TextField(blank=True)
    
    # Snapshot data (frozen at submission)
    cpi_at_apply = models.DecimalField(max_digits=4, decimal_places=2, null=True, blank=True)
    semester_at_apply = models.PositiveSmallIntegerField(null=True, blank=True)
    standing_declared_seq_at_apply = models.IntegerField(null=True, blank=True)
    eligibility_snapshot = models.JSONField(default=dict, blank=True)
    
    # Audit/Lifecycle tracking
    withdrawn_reason = models.CharField(max_length=300, blank=True)

    class Meta:
        db_table = "leave_application"
        constraints = [
            models.UniqueConstraint(fields=["category", "user_id"],
                                    name="application_unique_per_category"),
        ]
        indexes = [
            # Shortened index names
            models.Index(fields=["category"], name="app_cat_idx"),
            models.Index(fields=["user_id"], name="app_user_idx"),
        ]

    def __str__(self) -> str:
        return f"app#{self.pk} u{self.user_id} {self.category.code} ({self.start_date} to {self.end_date})"


class LeaveApplicationTransition(models.Model):
    """Append-only audit of every status change (PC-BR-008)."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=24)
    to_status = models.CharField(max_length=24)
    actor_user_id = models.IntegerField(null=True, blank=True)       # institute person
    actor_recruiter_id = models.IntegerField(null=True, blank=True)  # or a recruiter
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_transition"
        # Shortened index name
        indexes = [models.Index(fields=["application", "at"],
                                name="trans_app_idx")]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status}->{self.to_status}"


# --- Leave Balance ---
class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Tracks the current and historical balance for an employee/category/year."""
    
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="balances")
    
    user_id = models.IntegerField() # Employee ID
    year = models.IntegerField()
    
    # Balance is stored as float to handle half-day CL (0.5) and fractional conversions (2:1)
    balance_days = models.DecimalField(max_digits=5, decimal_places=2)
    
    # Tracks if this balance was derived from a conversion (e.g., VL->EL)
    is_converted = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_balance"
        unique_together = (('category', 'user_id', 'year'),)
        
    def __str__(self) -> str:
        return f"Balance for u{self.user_id} in {self.category.code} for {self.year}: {self.balance_days} days"
