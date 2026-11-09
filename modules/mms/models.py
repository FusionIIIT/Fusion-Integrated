"""Mess domain records. Institutional people are IAM ids, never local users."""
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class RoleAssignment(TimeStampedModel):
    ROLE = [("caretaker", "Mess Caretaker"), ("warden", "Mess Warden")]

    role = models.CharField(max_length=16, choices=ROLE, db_index=True)
    user_id = models.IntegerField(db_index=True)
    starts_at = models.DateTimeField()
    ends_at = models.DateTimeField()
    is_current = models.BooleanField(default=True)
    assigned_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_role_assignment"
        constraints = [
            models.CheckConstraint(condition=Q(ends_at__gt=models.F("starts_at")),
                                   name="mms_role_duration_valid"),
            models.UniqueConstraint(fields=["role"], condition=Q(is_current=True),
                                    name="mms_one_current_role"),
        ]
        indexes = [models.Index(fields=["role", "starts_at", "ends_at"],
                                name="mms_role_period_idx")]


class RegistrationWindow(TimeStampedModel):
    cycle = models.CharField(max_length=100, unique=True)
    opens_at = models.DateTimeField()
    closes_at = models.DateTimeField()
    opened_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_registration_window"
        constraints = [
            models.CheckConstraint(condition=Q(closes_at__gt=models.F("opens_at")),
                                   name="mms_window_dates_valid"),
        ]


class Enrollment(TimeStampedModel):
    user_id = models.IntegerField(unique=True, db_index=True)
    registered_at = models.DateTimeField()
    deregistered_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_enrollment"

    @property
    def is_registered(self):
        return self.deregistered_at is None


class StudentRequest(TimeStampedModel):
    KIND = [("registration", "Registration"), ("deregistration", "Deregistration")]
    STATUS = [
        ("pending", "Pending"), ("approved", "Approved"),
        ("approved_awaiting_effect", "Approved - awaiting effective date"),
        ("rejected", "Rejected"), ("effective", "Effective"),
    ]

    user_id = models.IntegerField(db_index=True)
    kind = models.CharField(max_length=20, choices=KIND)
    status = models.CharField(max_length=32, choices=STATUS, default="pending")
    window = models.ForeignKey(RegistrationWindow, null=True, blank=True,
                               on_delete=models.PROTECT, related_name="requests")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    effective_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_student_request"
        indexes = [models.Index(fields=["kind", "status", "created_at"],
                                name="mms_req_queue_idx")]
        constraints = [
            models.UniqueConstraint(fields=["user_id", "window"],
                                    condition=Q(kind="registration"),
                                    name="mms_one_registration_window"),
            models.UniqueConstraint(fields=["user_id"], condition=(
                Q(kind="deregistration", status__in=["pending",
                                                       "approved_awaiting_effect"])
            ), name="mms_one_pending_dereg"),
        ]


class RequestHistory(models.Model):
    request = models.ForeignKey(StudentRequest, on_delete=models.CASCADE,
                                related_name="history")
    status = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mms_request_history"
        ordering = ["at", "id"]

    def __str__(self):
        return f"Request {self.request_id}: {self.status}"


class MenuWeek(TimeStampedModel):
    week_start = models.DateField(unique=True)
    published_at = models.DateTimeField(null=True, blank=True)
    updated_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_menu_week"


class MenuEntry(TimeStampedModel):
    DAY = [(i, name) for i, name in enumerate(
        ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])]
    MEAL = [("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner")]
    week = models.ForeignKey(MenuWeek, on_delete=models.CASCADE, related_name="entries")
    day = models.PositiveSmallIntegerField(choices=DAY)
    meal = models.CharField(max_length=12, choices=MEAL)
    item = models.CharField(max_length=200, blank=True)

    class Meta:
        db_table = "mms_menu_entry"
        ordering = ["day", "meal", "id"]
        constraints = [
            models.UniqueConstraint(fields=["week", "day", "meal"],
                                    name="mms_menu_week_day_meal_uniq"),
            models.CheckConstraint(
                condition=Q(day__gte=0, day__lte=6),
                name="mms_menu_entry_day_valid"),
        ]


class RebateRequest(TimeStampedModel):
    REASON = [("medical", "Medical"), ("institute_leave", "Institute leave"),
              ("family_function", "Family function"), ("other", "Other")]
    STATUS = [("pending", "Pending"), ("approved", "Approved"),
              ("rejected", "Rejected")]
    user_id = models.IntegerField(db_index=True)
    reason = models.CharField(max_length=24, choices=REASON)
    explanation = models.TextField(blank=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default="pending")
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_rebate_request"
        indexes = [models.Index(fields=["user_id", "starts_on", "ends_on"],
                                name="mms_rebate_dates_idx")]


class RebateHistory(models.Model):
    request = models.ForeignKey(RebateRequest, on_delete=models.CASCADE,
                                related_name="history")
    status = models.CharField(max_length=12)
    actor_user_id = models.IntegerField(null=True, blank=True)
    note = models.CharField(max_length=300, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mms_rebate_history"
        ordering = ["at", "id"]

    def __str__(self):
        return f"Rebate {self.request_id}: {self.status}"


class VacationSurvey(TimeStampedModel):
    title = models.CharField(max_length=160)
    vacation_starts_on = models.DateField()
    vacation_ends_on = models.DateField()
    deadline = models.DateTimeField()
    created_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_vacation_survey"


class VacationResponse(TimeStampedModel):
    RESPONSE = [("yes", "Yes"), ("no", "No")]
    survey = models.ForeignKey(VacationSurvey, on_delete=models.CASCADE,
                               related_name="responses")
    user_id = models.IntegerField(db_index=True)
    response = models.CharField(max_length=3, choices=RESPONSE)
    is_default = models.BooleanField(default=False)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_vacation_response"
        constraints = [models.UniqueConstraint(fields=["survey", "user_id"],
                                               name="mms_survey_one_response")]


class SpecialFoodRequest(TimeStampedModel):
    REASON = [("illness", "Illness"), ("personal_event", "Personal event")]
    STATUS = [("requested", "Requested"), ("approved", "Approved"),
              ("rejected", "Rejected"), ("served", "Served"),
              ("cancelled", "Cancelled")]
    user_id = models.IntegerField(db_index=True)
    reason = models.CharField(max_length=20, choices=REASON)
    details = models.TextField(blank=True)
    requested_for = models.DateField()
    status = models.CharField(max_length=12, choices=STATUS, default="requested")
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by_user_id = models.IntegerField(null=True, blank=True)
    charge_amount = models.DecimalField(max_digits=9, decimal_places=2,
                                        null=True, blank=True)

    class Meta:
        db_table = "mms_special_food_request"
        indexes = [models.Index(fields=["status", "created_at"],
                                name="mms_special_queue_idx")]


class SpecialFoodHistory(models.Model):
    request = models.ForeignKey(SpecialFoodRequest, on_delete=models.CASCADE,
                                related_name="history")
    status = models.CharField(max_length=12)
    actor_user_id = models.IntegerField(null=True, blank=True)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mms_special_food_history"
        ordering = ["at", "id"]

    def __str__(self):
        return f"Special food {self.request_id}: {self.status}"


class MonthlyBill(TimeStampedModel):
    STATUS = [("generated", "Generated"), ("finalized", "Finalized"),
              ("published", "Published")]
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    daily_rate = models.DecimalField(max_digits=9, decimal_places=2)
    served_days = models.PositiveSmallIntegerField()
    special_food_charges = models.DecimalField(max_digits=10, decimal_places=2,
                                               default=0)
    rebate_deduction = models.DecimalField(max_digits=10, decimal_places=2,
                                           default=0)
    total = models.DecimalField(max_digits=11, decimal_places=2)
    status = models.CharField(max_length=12, choices=STATUS, default="generated")
    finalized_by_user_id = models.IntegerField(null=True, blank=True)
    finalized_at = models.DateTimeField(null=True, blank=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_monthly_bill"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "month"],
                                    name="mms_bill_student_month"),
            models.CheckConstraint(condition=Q(month__gte=1, month__lte=12),
                                   name="mms_bill_month_valid"),
        ]


class BillingInput(TimeStampedModel):
    """Institution-supplied rate and served-day facts consumed by monthly runs."""
    user_id = models.IntegerField(db_index=True)
    year = models.PositiveSmallIntegerField()
    month = models.PositiveSmallIntegerField()
    daily_rate = models.DecimalField(max_digits=9, decimal_places=2)
    served_days = models.PositiveSmallIntegerField()
    recorded_by_user_id = models.IntegerField()

    class Meta:
        db_table = "mms_billing_input"
        constraints = [
            models.UniqueConstraint(fields=["user_id", "year", "month"],
                                    name="mms_billing_input_student_month"),
            models.CheckConstraint(condition=Q(month__gte=1, month__lte=12),
                                   name="mms_billing_input_month_valid"),
        ]


class Feedback(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    message = models.TextField()

    class Meta:
        db_table = "mms_feedback"


class Announcement(TimeStampedModel):
    title = models.CharField(max_length=200)
    body = models.TextField()
    published_by_user_id = models.IntegerField()
    published_by_role = models.CharField(max_length=16)
    published_at = models.DateTimeField()

    class Meta:
        db_table = "mms_announcement"
        ordering = ["-published_at"]


class NotificationOutbox(TimeStampedModel):
    topic = models.CharField(max_length=60, db_index=True)
    dedupe_key = models.CharField(max_length=200, unique=True)
    recipient_user_id = models.IntegerField(null=True, blank=True)
    recipient_email = models.EmailField(blank=True)
    subject = models.CharField(max_length=200)
    body = models.TextField()
    status = models.CharField(max_length=12, default="pending")
    attempts = models.PositiveSmallIntegerField(default=0)
    last_error = models.CharField(max_length=300, blank=True)
    claimed_at = models.DateTimeField(null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "mms_notification_outbox"
        indexes = [
            models.Index(fields=["status", "created_at"], name="mms_outbox_queue_idx"),
            models.Index(fields=["status", "claimed_at"], name="mms_outbox_claim_idx"),
        ]
