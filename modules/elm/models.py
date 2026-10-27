"""Database models owned exclusively by the ELM module."""

from decimal import Decimal

from django.db import models
from django.db.models import F, Q

from core.db.mixins import TimeStampedModel, UserScopedModel
from modules.elm.domain.leave_policy import LeaveCategory

LEAVE_CATEGORY_CHOICES = tuple((category.value, category.value) for category in LeaveCategory)

LEAVE_APPLICATION_STATUS_CHOICES = [
    ("draft", "Draft / Not Submitted"),
    ("awaiting_substitute_response", "Awaiting Substitute Response"),
    ("applicant_action_required", "Applicant Action Required"),
    ("awaiting_unit_head_review", "Awaiting Unit Head Review"),
    ("awaiting_establishment_routing", "Awaiting Establishment Routing"),
    ("awaiting_final_sanction_decision", "Awaiting Final Sanction Decision"),
    ("awaiting_director_self_sanction", "Awaiting Director Self-Sanction"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("withdrawn", "Withdrawn"),
    ("cancelled", "Cancelled"),
]

TRANSACTION_TYPE_CHOICES = [
    ("annual_grant", "Annual grant"),
    ("leave_debit", "Leave debit"),
    ("restoration", "Restoration"),
    ("carry_forward_in", "Carry-forward in"),
    ("carry_forward_out", "Carry-forward out"),
    ("lapse", "Lapse"),
    ("vl_conversion_in", "VL conversion in"),
    ("vl_conversion_out", "VL conversion out"),
    ("manual_adjustment", "Manual adjustment"),
    ("offline_sanction", "Offline sanction"),
]

SUBSTITUTE_RESPONSE_CHOICES = [
    ("pending", "Pending"),
    ("accepted", "Accepted"),
    ("declined", "Declined"),
    ("cancelled", "Cancelled"),
]


class LeaveBalance(TimeStampedModel, UserScopedModel):
    """An employee's entitlement account for a year and leave category."""

    leave_year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=LEAVE_CATEGORY_CHOICES)
    annual_entitlement = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "leave_year", "category"],
                name="elm_balance_user_year_cat_uniq",
            ),
            models.CheckConstraint(
                condition=Q(annual_entitlement__gte=Decimal("0")),
                name="elm_balance_entitlement_nonneg",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_year"],
                name="elm_balance_user_year_idx",
            ),
        ]

    @property
    def current_balance(self) -> Decimal:
        """Return the net balance recorded in this account's transaction ledger."""
        if self.pk is None:
            return Decimal("0.00")

        total = self.transactions.aggregate(total=models.Sum("delta"))["total"]
        return total if total is not None else Decimal("0.00")

    def __str__(self) -> str:
        return f"Leave balance: user {self.user_id}, {self.category}, {self.leave_year}"


class LeaveApplication(TimeStampedModel, UserScopedModel):
    """One leave request, including any associated Station Leave details."""

    category = models.CharField(max_length=3, choices=LEAVE_CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    requested_days = models.DecimalField(max_digits=10, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(
        max_length=48,
        choices=LEAVE_APPLICATION_STATUS_CHOICES,
        default="draft",
        db_index=True,
    )

    half_day_portion = models.CharField(
        max_length=12,
        choices=[
            ("first_half", "First half"),
            ("second_half", "Second half"),
        ],
        blank=True,
        default="",
    )
    substitute_required = models.BooleanField(default=False)
    medical_evidence_reference = models.CharField(
        max_length=500,
        blank=True,
        default="",
    )
    responsibility_start_date = models.DateField(null=True, blank=True)
    responsibility_end_date = models.DateField(null=True, blank=True)
    station_leave_required = models.BooleanField(default=False)
    station_leave_details = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_leave_application"
        constraints = [
            models.CheckConstraint(
                condition=Q(end_date__gte=F("start_date")),
                name="elm_app_date_order_valid",
            ),
            models.CheckConstraint(
                condition=Q(requested_days__gt=Decimal("0")),
                name="elm_app_days_positive",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        half_day_portion="",
                        requested_days__gte=Decimal("1"),
                    )
                    | Q(
                        half_day_portion__in=["first_half", "second_half"],
                        category=LeaveCategory.CL.value,
                        start_date=F("end_date"),
                        requested_days=Decimal("0.50"),
                    )
                ),
                name="elm_app_halfday_valid",
            ),
            models.CheckConstraint(
                condition=(
                    Q(
                        responsibility_start_date__isnull=True,
                        responsibility_end_date__isnull=True,
                    )
                    | Q(
                        responsibility_start_date__isnull=False,
                        responsibility_end_date__isnull=False,
                        responsibility_end_date__gte=F("responsibility_start_date"),
                    )
                ),
                name="elm_app_responsibility_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "status"],
                name="elm_app_user_status_idx",
            ),
            models.Index(
                fields=["start_date", "end_date"],
                name="elm_app_dates_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Leave application #{self.pk}: user {self.user_id}, {self.category}, {self.status}"


class LeaveApplicationTransition(models.Model):
    """Audit record of a leave application's workflow transition."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.PROTECT,
        related_name="transitions",
    )
    from_status = models.CharField(max_length=48)
    to_status = models.CharField(max_length=48)
    action = models.CharField(max_length=48)
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True, default="")
    metadata = models.JSONField(default=dict, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_application_transition"
        indexes = [
            models.Index(
                fields=["application", "at"],
                name="elm_transition_app_at_idx",
            ),
        ]
        ordering = ["at", "pk"]

    def __str__(self) -> str:
        return f"Application #{self.application_id}: {self.from_status} -> {self.to_status}"


class SubstituteConsent(models.Model):
    """One substitute nomination and its response for a leave application."""

    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.PROTECT,
        related_name="substitute_consents",
    )
    substitute_user_id = models.IntegerField(db_index=True)
    nominated_by_user_id = models.IntegerField(null=True, blank=True)
    response_status = models.CharField(
        max_length=12,
        choices=SUBSTITUTE_RESPONSE_CHOICES,
        default="pending",
    )
    nominated_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    note = models.TextField(blank=True, default="")

    class Meta:
        db_table = "elm_substitute_consent"
        constraints = [
            models.UniqueConstraint(
                fields=["application", "substitute_user_id"],
                name="elm_sub_consent_nominee_uniq",
            ),
        ]
        indexes = [
            models.Index(
                fields=["application", "response_status"],
                name="elm_sub_consent_status_idx",
            ),
        ]
        ordering = ["nominated_at", "pk"]

    def __str__(self) -> str:
        return (
            f"Application #{self.application_id}: "
            f"substitute {self.substitute_user_id} ({self.response_status})"
        )


class LeaveAccountTransaction(models.Model):
    """A signed adjustment to an employee's leave account.

    Account entries are the balance ledger. Future domain services must append
    compensating transactions instead of rewriting historical entries.
    """

    balance = models.ForeignKey(
        LeaveBalance,
        on_delete=models.PROTECT,
        related_name="transactions",
    )
    application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.PROTECT,
        related_name="account_transactions",
        null=True,
        blank=True,
    )
    delta = models.DecimalField(max_digits=12, decimal_places=2)
    transaction_type = models.CharField(
        max_length=24,
        choices=TRANSACTION_TYPE_CHOICES,
    )
    effective_date = models.DateField()
    actor_user_id = models.IntegerField(null=True, blank=True)
    reference = models.CharField(max_length=120, blank=True, default="")
    note = models.TextField(blank=True, default="")
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "elm_leave_account_transaction"
        constraints = [
            models.CheckConstraint(
                condition=Q(delta__gt=Decimal("0")) | Q(delta__lt=Decimal("0")),
                name="elm_tx_delta_nonzero",
            ),
        ]
        indexes = [
            models.Index(
                fields=["balance", "effective_date"],
                name="elm_tx_balance_date_idx",
            ),
            models.Index(
                fields=["application", "effective_date"],
                name="elm_tx_app_date_idx",
            ),
        ]
        ordering = ["effective_date", "recorded_at", "pk"]

    def __str__(self) -> str:
        return f"{self.transaction_type}: {self.delta} for balance #{self.balance_id}"
