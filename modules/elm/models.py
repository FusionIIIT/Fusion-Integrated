from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeavePolicy(TimeStampedModel):
    CATEGORY_CHOICES = [(c,c) for c in ("CL","RH","SCL","EL","COL","VL")]
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES, unique=True)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carry_forward = models.BooleanField(default=False)
    half_day_allowed = models.BooleanField(default=False)
    continuous_days = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_policy"


class Holiday(TimeStampedModel):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=160)
    is_restricted = models.BooleanField(default=False)
    published = models.BooleanField(default=False)

    class Meta:
        db_table = "elm_holiday"
        ordering = ["date"]


class LeaveBalance(TimeStampedModel, UserScopedModel):
    year = models.PositiveIntegerField()
    category = models.CharField(max_length=8)
    entitled = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    used = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    carried_forward = models.DecimalField(max_digits=7, decimal_places=2, default=0)

    class Meta:
        db_table = "elm_leave_balance"
        constraints = [models.UniqueConstraint(fields=["user_id","year","category"], name="elm_balance_unique")]

    @property
    def available(self):
        return self.entitled + self.carried_forward - self.used


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [(c,c) for c in ("CL","RH","SCL","EL","COL","VL")]
    STATUS_CHOICES = [(s,s.replace("_"," ").title()) for s in (
        "draft","awaiting_substitute_response","awaiting_unit_head_review",
        "awaiting_establishment_verification","awaiting_final_sanction",
        "approved","rejected","withdrawn","cancellation_requested",
        "cancelled","extension_requested","awaiting_resumption_review","completed") ]
    HALF_CHOICES = [("full","Full day"),("first","First half"),("second","Second half")]
    category = models.CharField(max_length=8, choices=CATEGORY_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    half = models.CharField(max_length=8, choices=HALF_CHOICES, default="full")
    days = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    reason = models.TextField(blank=True)
    station_leave_details = models.TextField(blank=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, blank=True)
    status = models.CharField(max_length=40, choices=STATUS_CHOICES, default="draft")
    decision = models.CharField(max_length=16, blank=True)
    decision_note = models.TextField(blank=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    medical_evidence = models.TextField(blank=True)
    actual_resumption_date = models.DateField(null=True, blank=True)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user_id","status"]), models.Index(fields=["category","status"])]


class LeaveAction(TimeStampedModel):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name="actions")
    actor_user_id = models.IntegerField(null=True, blank=True)
    action = models.CharField(max_length=48)
    from_status = models.CharField(max_length=40, blank=True)
    to_status = models.CharField(max_length=40, blank=True)
    note = models.TextField(blank=True)

    class Meta:
        db_table = "elm_leave_action"
        ordering = ["created_at"]


class SlaConfig(TimeStampedModel):
    task_type = models.CharField(max_length=64, unique=True)
    reminder_hours = models.PositiveIntegerField(default=24)
    escalation_hours = models.PositiveIntegerField(default=48)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_sla_config"
