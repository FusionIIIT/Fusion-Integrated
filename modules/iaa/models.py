"""IAA-owned tables; identity is referenced by integer, never a cross-module FK."""

from django.db import models

from modules.iaa.domain.rules import Role, State


class IaaModel(models.Model):
    class Meta:
        abstract = True

    def __str__(self):
        return str(
            getattr(self, "name", None)
            or getattr(self, "code", None)
            or f"{self._meta.verbose_name} #{self.pk}"
        )


class RoleAssignment(IaaModel):
    user_id = models.PositiveIntegerField()
    role = models.CharField(max_length=24, choices=[(r.value, r.value) for r in Role])
    department = models.CharField(max_length=80, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_role_assignment"
        constraints = [
            models.UniqueConstraint(
                fields=["user_id", "role", "department"], name="iaa_role_scope_unique"
            )
        ]


class FinancialYear(IaaModel):
    name = models.CharField(max_length=32, unique=True)
    starts_on = models.DateField()
    ends_on = models.DateField()
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_financial_year"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ends_on__gte=models.F("starts_on")),
                name="iaa_year_dates_ordered",
            )
        ]


class Department(IaaModel):
    code = models.CharField(max_length=80, unique=True)
    finance_user_id = models.PositiveIntegerField()

    class Meta:
        db_table = "iaa_department"


class Policy(IaaModel):
    name = models.CharField(max_length=80, unique=True)
    ta_approval_threshold = models.DecimalField(max_digits=14, decimal_places=2)
    ta_max_daily_amount = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True
    )
    documents_required = models.BooleanField(default=True)
    budget_required = models.BooleanField(default=True)
    anomaly_resolver_id = models.PositiveIntegerField()
    anomaly_resolver_role = models.CharField(max_length=24)
    anomaly_escalation_id = models.PositiveIntegerField(null=True, blank=True)
    anomaly_escalation_role = models.CharField(max_length=24, blank=True)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_policy"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(ta_approval_threshold__gte=0), name="iaa_threshold_non_negative"
            )
        ]


class ApprovalRoute(IaaModel):
    name = models.CharField(max_length=80, unique=True)
    department = models.CharField(max_length=80, blank=True)
    request_type = models.CharField(max_length=80, blank=True)
    kind = models.CharField(max_length=8, choices=[("expense", "Expense"), ("ta", "TA")])
    minimum = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    maximum = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    priority = models.PositiveIntegerField(default=100)
    steps = models.JSONField(default=list)
    active = models.BooleanField(default=True)

    class Meta:
        db_table = "iaa_approval_route"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(minimum__gte=0), name="iaa_route_min_non_negative"
            ),
            models.CheckConstraint(
                condition=models.Q(maximum__isnull=True)
                | models.Q(maximum__gt=models.F("minimum")),
                name="iaa_route_amount_ordered",
            ),
        ]


class Budget(IaaModel):
    department = models.CharField(max_length=80)
    year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT)
    allocated = models.DecimalField(max_digits=14, decimal_places=2)

    class Meta:
        db_table = "iaa_budget"
        constraints = [
            models.UniqueConstraint(fields=["department", "year"], name="iaa_budget_scope_unique"),
            models.CheckConstraint(
                condition=models.Q(allocated__gte=0), name="iaa_budget_non_negative"
            ),
        ]


class FinancialRequest(IaaModel):
    creator_id = models.PositiveIntegerField()
    creator_role = models.CharField(max_length=24)
    kind = models.CharField(max_length=8, choices=[("expense", "Expense / voucher"), ("ta", "TA")])
    request_type = models.CharField(max_length=80, blank=True)
    department = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True)
    amount = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    documents = models.JSONField(default=list)
    trip_start = models.DateField(null=True, blank=True)
    trip_end = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=24, choices=[(s.value, s.value) for s in State], default=State.DRAFT
    )
    finance_user_id = models.PositiveIntegerField(null=True, blank=True)
    recovery_note = models.CharField(max_length=255, blank=True)
    year = models.ForeignKey(FinancialYear, on_delete=models.PROTECT, null=True, blank=True)
    policy_snapshot = models.JSONField(default=dict)
    route_snapshot = models.JSONField(default=list)
    route_index = models.PositiveIntegerField(default=0)
    assignee_id = models.PositiveIntegerField(null=True, blank=True)
    assignee_role = models.CharField(max_length=24, blank=True)
    assigned_at = models.DateTimeField(null=True, blank=True)
    budget = models.ForeignKey(Budget, on_delete=models.PROTECT, null=True, blank=True)
    reservation = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    processing_reference = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    recorded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iaa_financial_request"
        indexes = [
            models.Index(fields=["creator_id", "-id"], name="iaa_request_owner_idx"),
            models.Index(fields=["assignee_id", "status"], name="iaa_request_assignee_idx"),
            models.Index(fields=["department", "status"], name="iaa_request_dept_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(reservation__gte=0), name="iaa_reservation_non_negative"
            )
        ]


class Clarification(IaaModel):
    request = models.ForeignKey(
        FinancialRequest, on_delete=models.PROTECT, related_name="clarifications"
    )
    query = models.TextField()
    asked_by = models.PositiveIntegerField()
    response = models.TextField(blank=True)
    evidence = models.JSONField(default=list)
    asked_at = models.DateTimeField(auto_now_add=True)
    responded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "iaa_clarification"


class Anomaly(IaaModel):
    request = models.ForeignKey(
        FinancialRequest, on_delete=models.PROTECT, related_name="anomalies"
    )
    category = models.CharField(max_length=80)
    description = models.TextField()
    status = models.CharField(
        max_length=12, default="open", choices=[(s, s) for s in ("open", "resolved", "escalated")]
    )
    resolver_id = models.PositiveIntegerField()
    resolver_role = models.CharField(max_length=24)
    escalation_id = models.PositiveIntegerField(null=True, blank=True)
    escalation_role = models.CharField(max_length=24, blank=True)
    automatic = models.BooleanField(default=False)
    resolution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iaa_anomaly"
        indexes = [models.Index(fields=["resolver_id", "status"], name="iaa_anomaly_resolver_idx")]


class Observation(IaaModel):
    request = models.ForeignKey(
        FinancialRequest, on_delete=models.PROTECT, related_name="observations"
    )
    auditor_id = models.PositiveIntegerField()
    respondent_id = models.PositiveIntegerField()
    description = models.TextField()
    status = models.CharField(
        max_length=12, default="open", choices=[(s, s) for s in ("open", "responded", "closed")]
    )
    response = models.TextField(blank=True)
    evidence = models.JSONField(default=list)
    verification = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iaa_observation"
        indexes = [
            models.Index(fields=["respondent_id", "status"], name="iaa_observation_owner_idx")
        ]


class AuditEntry(IaaModel):
    actor_id = models.PositiveIntegerField(null=True)
    active_role = models.CharField(max_length=24)
    action = models.CharField(max_length=80)
    object_type = models.CharField(max_length=40)
    object_id = models.PositiveIntegerField(null=True)
    request = models.ForeignKey(
        FinancialRequest, on_delete=models.PROTECT, null=True, related_name="history"
    )
    from_status = models.CharField(max_length=24, blank=True)
    to_status = models.CharField(max_length=24, blank=True)
    details = models.JSONField(default=dict)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iaa_audit_entry"
        indexes = [models.Index(fields=["request", "id"], name="iaa_audit_request_idx")]


class Notification(IaaModel):
    user_id = models.PositiveIntegerField()
    role = models.CharField(max_length=24)
    request = models.ForeignKey(FinancialRequest, on_delete=models.PROTECT, null=True)
    event = models.CharField(max_length=80)
    message = models.CharField(max_length=255)
    at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "iaa_notification"
        indexes = [
            models.Index(fields=["user_id", "role", "-id"], name="iaa_notification_scope_idx")
        ]
