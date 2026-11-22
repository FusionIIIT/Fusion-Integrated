from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveCategory(TimeStampedModel):
    code = models.CharField(max_length=24, unique=True)
    label = models.CharField(max_length=80)
    description = models.TextField(blank=True)
    annual_entitlement = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    requires_substitute = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_category"
        ordering = ["label"]


class LeaveBalance(TimeStampedModel):
    user_id = models.PositiveIntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="balances")
    leave_year = models.CharField(max_length=9)
    opening = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    credited = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    pending = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [models.UniqueConstraint(
            fields=["user_id", "category", "leave_year"],
            name="elm_balance_user_category_year_unique")]

    @property
    def available(self):
        return self.opening + self.credited - self.used - self.pending


class LeaveApplication(TimeStampedModel):
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("withdrawn", "Withdrawn")]
    user_id = models.PositiveIntegerField(db_index=True)
    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="applications")
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.BooleanField(default=False)
    reason = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    current_stage = models.CharField(max_length=40, default="unit_head")
    substitute_user_id = models.PositiveIntegerField(null=True, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
    decision_note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["-submitted_at"]
        indexes = [models.Index(fields=["user_id", "status"],
                                name="elm_app_user_status_idx")]

    @property
    def day_count(self):
        days = (self.end_date - self.start_date).days + 1
        return 0.5 if self.half_day and days == 1 else days


class Holiday(TimeStampedModel):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=120)
    kind = models.CharField(max_length=24, default="holiday")
    is_restricted = models.BooleanField(default=False)
    published = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]
