"""Employee Leave Management request, balance, decision and substitution tables."""

from django.db import models
from django.db.models import Q
from django.utils import timezone

from core.db.mixins import TimeStampedModel


class LeaveApplication(TimeStampedModel):
    """A submitted leave request. Pending requests are immutable: change only by
    withdrawal + fresh application, or cancellation of an approved leave."""

    STATUS = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("awaiting_substitute", "Awaiting Substitute Response"),
        ("applicant_action_required", "Applicant Action Required"),
        ("unit_head_review", "Unit Head Review"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
        ("cancelled", "Cancelled"),
        ("withdrawn", "Withdrawn"),
        ("suspend", "Suspend"),
    ]

    CATEGORY = [
        ("CL", "Casual Leave"),
        ("RH", "Restricted Holiday"),
        ("SCL", "Special Casual Leave"),
        ("EL", "Earned Leave"),
        ("COL", "Complementary Leave"),
        ("VL", "Vacation Leave"),
        ("SL", "Station Leave"),
    ]

    applicant = models.IntegerField(
        db_column="applicant_id",
        db_index=True,
        help_text="IAM user id of the employee who owns this application.",
    )

    category = models.CharField(max_length=32, choices=CATEGORY)
    reason = models.TextField(blank=True)

    # The planned leave: dates may differ from the approved dates.
    requested_start = models.DateField()
    requested_end = models.DateField()
    actual_start = models.DateField(
        null=True,
        blank=True,
        help_text="Filled in by a resumed leave once the Sanctioning Authority confirms the real period.",
    )
    actual_end = models.DateField(
        null=True,
        blank=True,
        help_text="Filled in by a resumed leave once the Sanctioning Authority confirms the real period.",
    )

    station_leave = models.BooleanField(
        default=False,
        help_text="Permission/details for leaving Jabalpur, captured inside this application.",
    )
    station_leave_note = models.TextField(
        blank=True,
        help_text="Station Leave details live in the same application as the leave request.",
    )

    substitution_required = models.BooleanField(
        default=False,
        help_text="Responsibility coverage during the absence.",
    )
    substitute_applicant_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Nominated substitute/responsibility holder.",
    )

    # Approval state is kept here rather than in the `approved` row: an approved
    # leave moves the balance, a pending request does not, and a rejected one
    # changes neither.
    approved_start = models.DateField(
        null=True,
        blank=True,
        help_text="Date after which the approved leave is active.",
    )
    approved_end = models.DateField(
        null=True,
        blank=True,
        help_text="Approved end date; a resumption earlier or later than this triggers balance adjustment.",
    )
    approved_balance_deducted = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Leave balance already deduded for the approved leave.",
    )
    approval_note = models.TextField(blank=True)

    status = models.CharField(max_length=32, choices=STATUS, default="draft")
    current_step = models.CharField(
        max_length=64,
        blank=True,
        help_text="Current stage in the workflow, e.g. Awaiting Unit Head Review.",
    )
    recipient_user_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="Who the request is routed to next.",
    )
    decision = models.CharField(
        max_length=32,
        choices=[
            ("recommended", "Recommended"),
            ("not_recommended", "Not Recommended"),
            ("approved", "Approved"),
            ("rejected", "Rejected"),
        ],
        null=True,
        blank=True,
        help_text="The last recorded recommendation or final decision.",
    )

    # Year-end: records which account amendments were applied, so a rerun never
    # double-counts and the year-end report has a traceable ledger.
    year_end_applied = models.BooleanField(
        default=False,
        help_text="This request was processed by the year-end batch.",
    )
    year_end_exception = models.CharField(
        max_length=300,
        blank=True,
        help_text="Free text explanation for an exception, e.g. why conversion could not be applied.",
    )

    class Meta:
        db_table = "elm_leave_application"
        indexes = [
            models.Index(fields=["applicant", "category"], name="leave_applicant_category_idx"),
            models.Index(
                fields=["applicant", "status"],
                name="leave_applicant_status_idx",
            ),
            models.Index(
                fields=["applicant", "approved_start"],
                name="leave_applicant_approved_start",
            ),
            models.Index(
                fields=["applicant", "substitute_applicant_id"],
                name="leave_applicant_substitute",
            ),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(actual_start__isnull=True)
                | Q(actual_end__isnull=True)
                | Q(actual_start__lte=Q("actual_end")),
                name="resumption_dates_present",
            ),
            models.CheckConstraint(
                condition=Q(requested_end__gte=Q("requested_start"))
                | Q(requested_end__isnull=True),
                name="request_period_valid",
            ),
        ]

    def __str__(self) -> str:
        return f"leave#{self.pk} u{self.applicant_id} {self.get_category_display()}"

    @property
    def approved(self) -> bool:
        return self.status == "approved"

    @property
    def started(self) -> bool:
        return self.approved_start is not None and self.approved_start <= timezone.now().date()

    @property
    def requires_substitute_consent(self) -> bool:
        return self.substitution_required and not self.substitute_accepted

    @property
    def substitute_accepted(self) -> bool:
        # Consent is a subscription on the substituted row; the request itself
        # is only advanceable once that is recorded and the successor workflow
        # has a clean entry point.
        return (
            self.substitute_applicant_id is not None
            and LeaveApplication.objects.filter(
                applicant_id=self.substitute_applicant_id,
                substitution_applicant_id=self.applicant_id,
                status="awaiting_unit_head_review",
            ).exists()
        )


class LeaveSubstitution(TimeStampedModel):
    """Responsibility coverage assignment for an ongoing leave."""

    leave_application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="substitutions",
    )
    nominated_by_applicant_id = models.IntegerField(
        db_column="nominated_by_applicant_id",
    )
    substitute_applicant_id = models.IntegerField(
        db_column="substitute_applicant_id",
    )
    responsibility_start = models.DateField()
    responsibility_end = models.DateField()

    # The actual substitution row is the source of truth: the status text is a
    # projection of the workflow decisions recorded on leave_application.
    status = models.CharField(
        max_length=64,
        choices=[
            ("pending", "Pending substitute response"),
            ("accepted", "Accepted"),
            ("declined", "Declined"),
            ("replaced", "Replaced"),
        ],
        default="pending",
    )

    class Meta:
        db_table = "elm_leave_substitution"
        constraints = [
            models.UniqueConstraint(
                fields=["leave_application", "substitute_applicant_id"],
                name="leave_substitution_unique_substitute",
            ),
        ]

    def __str__(self) -> str:
        return f"sub u{self.nominated_by_applicant_id} -> u{self.substitute_applicant_id}"


class LeaveBalance(TimeStampedModel):
    """Per-applicant, per-category leave account, including year-end transmutations."""

    applicant = models.IntegerField(
        db_column="applicant_id",
        db_index=True,
        help_text="IAM user id of the employee who owns this account.",
    )

    category = models.CharField(max_length=32, choices=LeaveApplication.CATEGORY)
    balance = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Current yearly entitlement remaining.",
    )
    carried_forward = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Balance from a previous year, for carry-forward categories.",
    )
    year = models.PositiveIntegerField(
        db_index=True,
        help_text="Leave year, independent of calendar year for CL/SCL/RH.",
    )

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [
            models.UniqueConstraint(
                fields=["applicant", "category", "year"],
                name="leave_balance_unique_per_applicant_category_year",
            ),
        ]
        indexes = [
            models.Index(fields=["applicant", "year"], name="leave_balance_applicant_year"),
        ]

        constraints = [
            models.UniqueConstraint(fields=["applicant", "category", "year"], name="leave_balance_unique_per_applicant_category_year"),
        ]

    def __str__(self) -> str:
        return f"u{self.applicant_id} {self.get_category_display()} {self.year} balance={self.balance}"


class LeaveDecision(TimeStampedModel):
    """Append-only record of every final decision plus the historical route."""

    leave_application = models.ForeignKey(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="decisions",
    )
    actor_applicant_id = models.IntegerField(
        db_column="actor_applicant_id",
        null=True,
        blank=True,
    )
    category = models.CharField(max_length=32, db_index=True)
    decision = models.CharField(max_length=32, db_index=True)
    rationale = models.TextField(blank=True)
    requested_start = models.DateField()
    requested_end = models.DateField()

    class Meta:
        db_table = "elm_leave_decision"
        indexes = [        models.Index(
            fields=["leave_application", "decision"], name="leave_decision_app_decision"
        ),
        ]

    def __str__(self) -> str:
        return f"dec#{self.pk} {self.leave_application_id} {self.decision}"


class Resumption(TimeStampedModel):
    """Actual return-to-duty record for ongoing EL/COL/VL, reviewed by the
    Sanctioning Authority."""

    leave_application = models.OneToOneField(
        LeaveApplication,
        on_delete=models.CASCADE,
        related_name="resumption",
        primary_key=True,
    )
    actual_date = models.DateField(
        help_text="Employee's actual return-to-duty date.",
    )
    normal = models.BooleanField(
        default=False,
        help_text="Actual date equals approved end date; no adjustment.",
    )
    early = models.BooleanField(
        default=False,
        help_text="Actual date before approved end; balance adjusted.",
    )
    late = models.BooleanField(
        default=False,
        help_text="Actual date after approved end; balance adjusted.",
    )
    adjustment = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        default=0,
        help_text="Balance restatement caused by early/late resumption.",
    )

    class Meta:
        db_table = "elm_resumption"
        constraints = [
            models.CheckConstraint(
                condition=Q(normal=True) | Q(early=True) | Q(late=True),
                name="resumption_exclusive",
            ),
        ]

    def __str__(self) -> str:
        return f"resumption for leave#{self.leave_application_id}"
