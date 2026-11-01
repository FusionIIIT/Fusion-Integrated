from django.core.validators import MinValueValidator
from django.db import models

# --- Configuration Constants ---
# Leave Categories
LEAVE_CATEGORIES = (
    ("CL", "Casual Leave (CL)"),
    ("RH", "Restricted Holiday (RH)"),
    ("SCL", "Special Casual Leave (SCL)"),
    ("EL", "Earned Leave (EL)"),
    ("VL", "Vacation Leave (VL)"),
    ("COL", "Commuted Leave (COL)"),
)

# Leave Application Statuses
LEAVE_STATUS_CHOICES = (
    ("pending", "Pending Review"),
    ("recommended", "Recommended"),
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("cancelled", "Cancelled"),
)

# Substitute Response Statuses
SUBSTITUTE_RESPONSE_CHOICES = (
    ("pending", "Pending"),
    ("accepted", "Accepted"),
    ("declined", "Declined"),
)


class LeaveBalance(models.Model):
    """
    Tracks annual leave entitlement and available balance per employee and category.

    Uses string IDs for user reference (user_id).
    """

    # Since we cannot use Django ForeignKeys to other modules, we store the ID as a string.
    # We assume 'user_id' refers to the user identifier from the Fusion_System_Administrator module.
    user_id = models.CharField(max_length=64, verbose_name="Employee ID")

    category = models.CharField(
        max_length=3, choices=LEAVE_CATEGORIES, verbose_name="Leave Category"
    )

    # Annual entitlement (e.g., 30 days for EL)
    annual_entitlement = models.DecimalField(
        max_digits=5, decimal_places=1, default=0.0, help_text="Total days granted for the year"
    )

    # Current available balance
    available_balance = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Days currently available",
    )

    class Meta:
        # A user should only have one balance record per category
        unique_together = ("user_id", "category")
        verbose_name = "Leave Balance"
        verbose_name_plural = "Leave Balances"

    def __str__(self):
        desc = self.get_category_display()
        return f"Balance for {self.user_id} - {desc}: {self.available_balance} days"


class LeaveApplication(models.Model):
    """
    Details of a leave request submitted by an employee.
    """

    # Employee submitting the leave (string ID)
    employee_id = models.CharField(max_length=64, verbose_name="Employee ID")

    # Substitute coverage nomination (string ID, can be blank)
    substitute_id = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Substitute Employee ID"
    )

    category = models.CharField(
        max_length=3, choices=LEAVE_CATEGORIES, verbose_name="Leave Category"
    )

    start_date = models.DateField(verbose_name="Start Date")
    end_date = models.DateField(verbose_name="End Date")

    # Flag for when the employee is outside their usual work station
    is_station_leave = models.BooleanField(default=False, verbose_name="Is Station Leave")

    is_half_day_start = models.BooleanField(default=False, verbose_name="Half Day Start")
    is_half_day_end = models.BooleanField(default=False, verbose_name="Half Day End")
    reason = models.TextField(verbose_name="Reason for Leave")

    # Status tracking the lifecycle of the request
    status = models.CharField(
        max_length=20,
        choices=LEAVE_STATUS_CHOICES,
        default="pending",
        verbose_name="Application Status",
    )

    # Used internally to track approval chain (Approver ID, HOD ID, etc.)
    recommended_by_id = models.CharField(
        max_length=64, blank=True, default="", verbose_name="Recommended By Employee ID"
    )

    approved_by_id = models.CharField(
        max_length=64,
        blank=True,
        default="",
        verbose_name="Approved By Employee ID (Final Sanction)",
    )

    # Calculated duration in days (may differ from actual calculation due to system rules)
    duration_days = models.DecimalField(
        max_digits=5, decimal_places=1, default=0.0, help_text="Calculated duration of the leave."
    )

    class Meta:
        ordering = ["start_date"]
        verbose_name = "Leave Application"
        verbose_name_plural = "Leave Applications"

    def __str__(self):
        return (
            f"App {self.id}: {self.category} ({self.start_date} to {self.end_date}) [{self.status}]"
        )


class SubstituteResponse(models.Model):
    """
    Tracks the consent response of the nominated substitute employee.
    """

    application_id = models.ForeignKey(
        "LeaveApplication",
        on_delete=models.CASCADE,
        related_name="substitute_responses",
        verbose_name="Leave Application",
    )

    # The employee who was nominated as substitute (string ID)
    substitute_id = models.CharField(max_length=64, verbose_name="Substitute Employee ID")

    response_status = models.CharField(
        max_length=20,
        choices=SUBSTITUTE_RESPONSE_CHOICES,
        default="pending",
        verbose_name="Response Status",
    )

    notes = models.TextField(blank=True, default="")

    class Meta:
        # Ensure only one response record exists per application/substitute pair
        unique_together = ("application_id", "substitute_id")
        verbose_name = "Substitute Response"
        verbose_name_plural = "Substitute Responses"

    def __str__(self):
        status_disp = self.get_response_status_display()
        return f"Response for App {self.application_id} by {self.substitute_id}: {status_disp}"
