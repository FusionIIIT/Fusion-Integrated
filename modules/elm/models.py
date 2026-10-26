from django.db import models

from core.db.mixins import TimeStampedModel


class LeaveType(TimeStampedModel):
    """Represents different types of leaves available."""
    code = models.CharField(max_length=48, unique=True)
    label = models.CharField(max_length=80)
    description = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_type"
        ordering = ["label"]

    def __str__(self) -> str:
        return self.label


class LeaveBalance(TimeStampedModel):
    """Represents the balance of leaves for a user."""
    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "elm_leave_balance"
        unique_together = ("user", "leave_type")
        ordering = ["user", "leave_type"]

    def __str__(self) -> str:
        return f"{self.user} - {self.leave_type}"


class LeaveApplication(TimeStampedModel):
    """Represents a leave application made by a user."""
    class Status(models.TextChoices):
        DRAFT = 'draft', 'Draft'
        AWAITING_SUBSTITUTE_RESPONSE = (
            'awaiting_substitute_response',
            'Awaiting Substitute Response'
        )
        APPLICANT_ACTION_REQUIRED = 'applicant_action_required', 'Applicant Action Required'
        AWAITING_UNIT_HEAD_REVIEW = 'awaiting_unit_head_review', 'Awaiting Unit Head Review'
        APPROVED = 'approved', 'Approved'
        REJECTED = 'rejected', 'Rejected'
        WITHDRAWN = 'withdrawn', 'Withdrawn'
        CANCELLED = 'cancelled', 'Cancelled'
        AWAITING_FINAL_SANCTION_DECISION = (
            'awaiting_final_sanction_decision',
            'Awaiting Final Sanction Decision'
        )

    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=50,
        db_index=True,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    reason = models.TextField()
    unit_head_recommendation = models.CharField(max_length=50, blank=True)
    final_decision = models.CharField(max_length=20, blank=True)
    final_decision_date = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_application"
        ordering = ["user", "start_date"]

    def __str__(self) -> str:
        return f"{self.user} - {self.leave_type} - {self.start_date} to {self.end_date}"


class SubstituteNominee(TimeStampedModel):
    """Represents a substitute nominee for a leave application."""
    class NominationStatus(models.TextChoices):
        PENDING = 'pending', 'Pending'
        ACCEPTED = 'accepted', 'Accepted'
        DECLINED = 'declined', 'Declined'

    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    user = models.ForeignKey('directory.UserRef', on_delete=models.CASCADE)
    status = models.CharField(
        max_length=20,
        choices=NominationStatus.choices,
        default=NominationStatus.PENDING,
    )

    class Meta:
        db_table = "elm_substitute_nominee"
        unique_together = ("leave_application", "user")
        ordering = ["leave_application", "user"]

    def __str__(self) -> str:
        return f"{self.leave_application} - {self.user}"
