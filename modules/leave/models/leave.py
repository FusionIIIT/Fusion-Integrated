from django.db import models


class LeavePolicy(models.Model):
    year = models.PositiveSmallIntegerField(unique=True)
    values = models.JSONField(default=dict)
    hierarchy = models.JSONField(default=dict)
    reminder_hours = models.PositiveIntegerField(default=48)
    escalation_hours = models.PositiveIntegerField(default=96)
    updated_by = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_policy"

    def __str__(self):
        return f"Leave policy {self.year}"


class HolidayCalendar(models.Model):
    year = models.PositiveSmallIntegerField()
    version = models.PositiveIntegerField(default=1)
    published = models.BooleanField(default=False)
    holidays = models.JSONField(default=list)
    published_at = models.DateTimeField(null=True, blank=True)
    published_by = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "leave_holiday_calendar"
        constraints = [
            models.UniqueConstraint(fields=["year", "version"], name="leave_calendar_version")
        ]

    def __str__(self):
        return f"Holiday calendar {self.year} v{self.version}"


class LeaveAccount(models.Model):
    user_id = models.IntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3)
    is_faculty = models.BooleanField(default=False)
    balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    carried = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_account"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "year", "category"], name="leave_account_unique"
            )
        ]
        indexes = [models.Index(fields=["user_id", "year"], name="leave_account_user_year")]

    def __str__(self):
        return f"Leave account u{self.user_id} {self.year} {self.category}"


class LeaveApplication(models.Model):
    CATEGORIES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    TYPES = [("new", "New"), ("cancellation", "Cancellation"), ("extension", "Extension")]
    STATES = [
        (x, x)
        for x in (
            "draft",
            "awaiting_substitute",
            "applicant_action",
            "unit_head_review",
            "establishment_routing",
            "final_sanction",
            "director_self_sanction",
            "approved",
            "rejected",
            "withdrawn",
            "cancelled",
            "resumption_review",
        )
    ]
    user_id = models.IntegerField()
    category = models.CharField(max_length=3, choices=CATEGORIES)
    request_type = models.CharField(max_length=16, choices=TYPES, default="new")
    base_leave_id = models.IntegerField(null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=8, blank=True)
    purpose = models.TextField()
    station_leave = models.JSONField(default=dict, blank=True)
    medical_evidence = models.JSONField(default=dict, blank=True)
    chargeable_days = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    substitute_required = models.BooleanField(default=False)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    state = models.CharField(max_length=32, choices=STATES, default="draft")
    unit_head_user_id = models.IntegerField(null=True, blank=True)
    final_authority_user_id = models.IntegerField(null=True, blank=True)
    route = models.JSONField(default=dict, blank=True)
    recommendation = models.CharField(max_length=20, blank=True)
    decision_reason = models.TextField(blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "leave_application"
        indexes = [
            models.Index(fields=["user_id", "state"], name="leave_app_user_state"),
            models.Index(fields=["state", "unit_head_user_id"], name="leave_app_task"),
        ]

    def __str__(self):
        return f"Leave application #{self.pk} u{self.user_id} {self.category}"


class LeaveTransition(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="transitions"
    )
    from_state = models.CharField(max_length=32)
    to_state = models.CharField(max_length=32)
    actor_user_id = models.IntegerField(null=True, blank=True)
    reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_transition"

    def __str__(self):
        return f"Leave transition #{self.pk} {self.from_state}->{self.to_state}"


class SubstituteRequest(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="substitute_requests"
    )
    substitute_user_id = models.IntegerField()
    response = models.CharField(
        max_length=8,
        choices=[("pending", "Pending"), ("accepted", "Accepted"), ("declined", "Declined")],
        default="pending",
    )
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_substitute_request"

    def __str__(self):
        return f"Substitute request #{self.pk}"


class LeaveResumption(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="resumptions"
    )
    actual_date = models.DateField()
    details = models.TextField()
    state = models.CharField(max_length=24, default="pending")
    reviewed_by = models.IntegerField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "leave_resumption"

    def __str__(self):
        return f"Resumption #{self.pk}"


class LeaveLedger(models.Model):
    account = models.ForeignKey(LeaveAccount, on_delete=models.CASCADE, related_name="ledger")
    application_id = models.IntegerField(null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    kind = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_ledger"

    def __str__(self):
        return f"Leave ledger #{self.pk} {self.kind}"


class LeaveSlaEvent(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="sla_events"
    )
    kind = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"SLA event #{self.pk} {self.kind}"


class LeaveNotification(models.Model):
    application = models.ForeignKey(
        LeaveApplication, on_delete=models.CASCADE, related_name="notifications"
    )
    user_id = models.IntegerField()
    kind = models.CharField(max_length=24)
    read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "leave_notification"
        indexes = [models.Index(fields=["user_id", "read"], name="leave_notification_user")]

    def __str__(self):
        return f"Leave notification #{self.pk} {self.kind}"
