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
        ("COL", "Commuted Leave"), ("VL", "Vacation Leave"),
    ]
    code = models.CharField(max_length=3, unique=True, choices=CODE_CHOICES)
    name = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    is_carry_forwardable = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_category"

    def __str__(self) -> str:
        return f"{self.code} - {self.name}"


# --- Leave Application ---
class LeaveApplication(TimeStampedModel, UserScopedModel):
    """Represents a single leave request following the ELM workflow."""

    KIND_CHOICES = [("new", "New leave"), ("extension", "Extension of ongoing leave")]
    HALF_CHOICES = [("first", "First half"), ("second", "Second half")]
    RECOMMENDATION_CHOICES = [
        ("recommended", "Recommended"), ("not_recommended", "Not recommended"),
    ]
    SUBSTITUTE_RESPONSE_CHOICES = [
        ("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined"),
    ]
    RESUMPTION_CHOICES = [
        ("none", "Not submitted"),
        ("pending", "Review pending"),
        ("reviewed_no_adjustment", "Reviewed - no adjustment"),
        ("reviewed_early", "Reviewed - early return synchronized"),
        ("reviewed_late", "Reviewed - late return synchronized"),
    ]

    STATUS_CHOICES = [
        ("awaiting_substitute", "Awaiting substitute response"),
        ("applicant_action_required", "Applicant action required"),
        ("awaiting_unit_head", "Awaiting Unit Head review"),
        ("awaiting_establishment", "Awaiting Establishment routing"),
        ("awaiting_final_sanction", "Awaiting final sanction decision"),
        ("awaiting_director_self_sanction", "Awaiting Director self-sanction"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("withdrawn", "Withdrawn"),
        ("cancellation_pending_unit_head", "Cancellation pending - Unit Head"),
        ("cancellation_pending_establishment", "Cancellation pending - Establishment"),
        ("cancellation_pending_final", "Cancellation pending - final decision"),
        ("cancelled", "Cancelled"),
    ]

    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="applications")

    # Self-referential FK for extensions
    parent = models.ForeignKey("self", on_delete=models.PROTECT,
                                 null=True, blank=True, related_name="extensions")

    status = models.CharField(max_length=40, choices=STATUS_CHOICES,
                               default="awaiting_unit_head", db_index=True)

    start_date = models.DateField()
    end_date = models.DateField()

    half_day = models.CharField(max_length=6, choices=HALF_CHOICES,
                                 blank=True, default="")

    days_charged = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    balance_deducted = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    reason = models.TextField()
    is_station_leave = models.BooleanField(default=False)
    station_details = models.JSONField(default=dict, blank=True)

    medical_evidence_ref = models.CharField(max_length=300, blank=True)

    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_response = models.CharField(max_length=10,
                                            choices=SUBSTITUTE_RESPONSE_CHOICES,
                                            default="pending")

    recommendation = models.CharField(max_length=20,
                                      choices=RECOMMENDATION_CHOICES,
                                      blank=True, default="")

    applicant_is_director = models.BooleanField(default=False)

    withdrawn_reason = models.CharField(max_length=300, blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)
    resumption_status = models.CharField(max_length=30,
                                          choices=RESUMPTION_CHOICES,
                                          default="none")

    class Meta:
        db_table = "leave_application"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(end_date__gte=models.F('start_date')),
                name="leave_end_not_before_start",
            ),
            models.CheckConstraint(
                condition=models.Q(half_day="") | models.Q(start_date=models.F("end_date")),
                name="leave_half_day_single_day",
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "status"], name="leave_app_user_status_idx"),
            models.Index(fields=["category", "start_date"], name="leave_app_cat_start_idx"),
        ]

    def __str__(self) -> str:
        return (f"app#{self.pk} u{self.user_id} {self.category.code} "
                f"{self.start_date}..{self.end_date} [{self.status}]")


class LeaveApplicationTransition(models.Model):
    """Append-only audit of every status change (CFR-EL-016.4)."""

    application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE,
                                    related_name="transitions")
    from_status = models.CharField(max_length=40)
    to_status = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    actor_label = models.CharField(max_length=80, blank=True)
    reason = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_application_transition"
        indexes = [models.Index(fields=["application", "at"],
                                name="leave_trans_app_idx")]

    def __str__(self) -> str:
        return f"app#{self.application_id} {self.from_status}->{self.to_status}"


# --- Leave Balance ---
class LeaveBalance(TimeStampedModel, UserScopedModel):
    """Tracks the current and historical balance for an employee/category/year."""

    category = models.ForeignKey(LeaveCategory, on_delete=models.PROTECT,
                                 related_name="balances")

    year = models.IntegerField()

    # Balance is stored as decimal to handle fractional conversions
    balance_days = models.DecimalField(max_digits=6, decimal_places=2)

    # Tracks if this balance was derived from a conversion (e.g., VL->EL)
    is_converted = models.BooleanField(default=False)

    class Meta:
        db_table = "leave_balance"
        constraints = [
            models.UniqueConstraint(fields=["category", "user_id", "year"],
                                    name="leave_balance_unique_per_year"),
            models.CheckConstraint(
                condition=models.Q(balance_days__gte=0),
                name="leave_balance_not_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["category", "year"], name="balance_cat_year_idx"),
        ]

    def __str__(self) -> str:
        return (f"Balance for u{self.user_id} in {self.category.code} for {self.year}: "
                f"{self.balance_days} days")
