"""ELM domain records. Institute users are IAM IDs, not local FK rows."""
from django.db import models
from core.db.mixins import TimeStampedModel, UserScopedModel


class LeavePolicy(TimeStampedModel):
    category = models.CharField(max_length=8, unique=True)
    annual_entitlement = models.DecimalField(max_digits=7, decimal_places=2, default=0)
    requires_substitute = models.BooleanField(default=False)
    higher_sanction = models.BooleanField(default=False)
    enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "elm_leave_policy"


class LeaveRequest(TimeStampedModel, UserScopedModel):
    CATEGORIES = [(x, x) for x in ("CL", "RH", "SCL", "EL", "COL", "VL")]
    STATES = [(x, x.replace("_", " ").title()) for x in (
        "draft", "awaiting_substitute_response", "applicant_action_required",
        "awaiting_unit_head_review", "awaiting_establishment_routing",
        "awaiting_final_sanction_decision", "awaiting_director_self_sanction",
        "approved", "rejected", "withdrawn", "cancellation_pending",
        "cancelled", "extension_pending", "resumption_review_pending",
        "resumption_reviewed")]
    category = models.CharField(max_length=8, choices=CATEGORIES)
    start_date = models.DateField()
    end_date = models.DateField()
    days = models.DecimalField(max_digits=6, decimal_places=2)
    purpose = models.TextField()
    station_leave = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=48, choices=STATES, default="draft", db_index=True)
    substitute_user_id = models.IntegerField(null=True, blank=True)
    substitute_decision = models.CharField(max_length=12, blank=True)
    unit_head_decision = models.CharField(max_length=20, blank=True)
    final_decision = models.CharField(max_length=12, blank=True)
    decision_reason = models.TextField(blank=True)
    parent_request = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT,
                                     related_name="related_requests")
    version = models.PositiveIntegerField(default=1)

    class Meta:
        db_table = "elm_leave_request"
        ordering = ["-created_at"]
        constraints = [models.CheckConstraint(condition=models.Q(end_date__gte=models.F("start_date")), name="elm_leave_dates_ordered")]
        indexes = [models.Index(fields=["user_id", "status"], name="elm_user_status_idx"),
                  models.Index(fields=["start_date", "end_date"], name="elm_leave_dates_idx")]


class LeaveAccount(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    category = models.CharField(max_length=8)
    balance = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    year = models.PositiveSmallIntegerField()
    class Meta:
        db_table = "elm_leave_account"
        constraints = [models.UniqueConstraint(fields=["user_id", "category", "year"], name="elm_account_user_category_year_uniq")]


class LeaveTransaction(TimeStampedModel):
    account = models.ForeignKey(LeaveAccount, on_delete=models.PROTECT, related_name="transactions")
    request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.PROTECT)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    transaction_type = models.CharField(max_length=24)
    reference = models.CharField(max_length=120, blank=True)
    actor_user_id = models.IntegerField(null=True, blank=True)
    class Meta:
        db_table = "elm_leave_transaction"


class LeaveCalendarDay(TimeStampedModel):
    date = models.DateField(unique=True)
    day_type = models.CharField(max_length=16, choices=[("holiday", "Holiday"), ("rh", "Restricted Holiday")])
    label = models.CharField(max_length=160)
    published = models.BooleanField(default=False)
    class Meta:
        db_table = "elm_calendar_day"
