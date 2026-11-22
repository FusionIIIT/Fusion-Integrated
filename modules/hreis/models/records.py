from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel


class EmployeeServiceRecord(TimeStampedModel):
    EMPLOYEE_CATEGORIES = [
        ("faculty", "Faculty"),
        ("teaching_staff", "Teaching staff"),
        ("non_teaching_staff", "Non-teaching staff"),
    ]

    user_id = models.IntegerField(unique=True)
    employee_category = models.CharField(max_length=24, choices=EMPLOYEE_CATEGORIES)
    appointment_details = models.JSONField(default=dict, blank=True)
    department_code = models.CharField(max_length=80, blank=True)
    designation = models.CharField(max_length=120, blank=True)
    service_history = models.JSONField(default=list, blank=True)
    retirement_status = models.CharField(max_length=40, blank=True)
    updated_by_user_id = models.IntegerField(null=True, blank=True)

    class Meta:
        db_table = "hreis_employee_service_record"

    def __str__(self):
        return f"service record for user {self.user_id}"


class HRPolicyVersion(TimeStampedModel):
    policy_name = models.CharField(max_length=80)
    version = models.PositiveIntegerField()
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    payload = models.JSONField(default=dict)

    class Meta:
        db_table = "hreis_policy_version"
        constraints = [
            models.UniqueConstraint(
                fields=["policy_name", "version"], name="hreis_policy_version_unique"
            ),
            models.CheckConstraint(
                condition=Q(effective_to__isnull=True)
                | Q(effective_to__gte=models.F("effective_from")),
                name="hreis_policy_dates_valid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["policy_name", "effective_from"], name="hreis_policy_effective_idx"
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("Policy versions are immutable; create a new version.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Policy versions cannot be deleted.")

    def __str__(self):
        return f"{self.policy_name} v{self.version}"


class HRRequest(TimeStampedModel):
    REQUEST_TYPES = [
        ("leave", "Leave"),
        ("appraisal", "Yearly appraisal"),
        ("ltc_advance", "LTC advance"),
        ("ltc_reimbursement", "LTC reimbursement"),
        ("cpda_advance", "CPDA advance"),
        ("cpda_reimbursement", "CPDA reimbursement"),
    ]
    STATES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("awaiting_hr_verification", "Awaiting HR verification"),
        ("reviewer_assigned_pending_review", "Reviewer assigned / pending review"),
        ("pending_current_authority", "Pending current authority"),
        ("pending_next_authority", "Pending next authority"),
        ("approved_leave_balance_updated", "Approved; leave balance updated"),
        ("approved_ltc_claim", "Approved LTC claim"),
        ("approved_cpda_claim", "Approved CPDA claim"),
        ("rejected", "Rejected"),
        ("finalized_archived_closed", "Finalized, archived and closed"),
        ("processed_financial_status_recorded", "Financial status recorded"),
    ]

    owner_user_id = models.IntegerField(db_index=True)
    submission_key = models.CharField(max_length=100, blank=True, default="")
    submission_fingerprint = models.CharField(max_length=64, blank=True, default="")
    request_type = models.CharField(max_length=24, choices=REQUEST_TYPES)
    state = models.CharField(max_length=48, choices=STATES, default="draft")
    cycle_key = models.CharField(max_length=48, blank=True)
    data = models.JSONField(default=dict)
    approval_route = models.JSONField(default=list)
    route_index = models.PositiveSmallIntegerField(default=0)
    current_authority_designation = models.CharField(max_length=120, blank=True)
    policy_version = models.ForeignKey(
        HRPolicyVersion, on_delete=models.PROTECT, null=True, blank=True, related_name="requests"
    )

    class Meta:
        db_table = "hreis_request"
        constraints = [
            models.UniqueConstraint(
                fields=["owner_user_id", "submission_key"], name="hreis_submission_key_unique"
            ),
            models.UniqueConstraint(
                fields=["owner_user_id", "request_type", "cycle_key"],
                condition=Q(request_type="appraisal"),
                name="hreis_appraisal_cycle_unique",
            ),
        ]
        indexes = [
            models.Index(fields=["owner_user_id", "state"], name="hreis_request_owner_state_idx"),
            models.Index(
                fields=["request_type", "state", "updated_at"], name="hreis_request_type_state_idx"
            ),
        ]

    def __str__(self):
        return f"{self.request_type} request #{self.pk} ({self.state})"


class RequestDecision(models.Model):
    request = models.ForeignKey(HRRequest, on_delete=models.PROTECT, related_name="decisions")
    from_state = models.CharField(max_length=48)
    event = models.CharField(max_length=32)
    to_state = models.CharField(max_length=48)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=120, blank=True)
    note = models.CharField(max_length=500, blank=True)
    idempotency_key = models.CharField(max_length=100, blank=True, default="")
    details_fingerprint = models.CharField(max_length=64, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_request_decision"
        indexes = [
            models.Index(fields=["request", "created_at"], name="hreis_decision_request_idx")
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["request", "idempotency_key"], name="hreis_decision_idempotency_unique"
            ),
        ]

    def __str__(self):
        return f"request #{self.request_id}: {self.event}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Request decisions are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Request decisions cannot be deleted.")


class LeaveBalanceEntry(TimeStampedModel):
    user_id = models.IntegerField(db_index=True)
    leave_type = models.CharField(max_length=32)
    delta_days = models.DecimalField(max_digits=8, decimal_places=2)
    request = models.ForeignKey(
        HRRequest, on_delete=models.PROTECT, related_name="balance_entries", null=True, blank=True
    )
    reason = models.CharField(max_length=300)
    actor_user_id = models.IntegerField()

    class Meta:
        db_table = "hreis_leave_balance_entry"
        constraints = [
            models.CheckConstraint(condition=~Q(delta_days=0), name="hreis_leave_entry_nonzero"),
        ]
        indexes = [
            models.Index(
                fields=["user_id", "leave_type", "created_at"], name="hreis_balance_user_type_idx"
            ),
        ]

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Leave balance entries are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Leave balance entries cannot be deleted.")


class AuditEvent(models.Model):
    user_id = models.IntegerField(db_index=True)
    actor_user_id = models.IntegerField()
    actor_role = models.CharField(max_length=120, blank=True)
    action = models.CharField(max_length=80)
    resource_type = models.CharField(max_length=40)
    resource_id = models.PositiveBigIntegerField()
    details = models.JSONField(default=dict, blank=True)
    occurred_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hreis_audit_event"
        indexes = [
            models.Index(fields=["user_id", "occurred_at"], name="hreis_audit_user_idx"),
        ]

    def __str__(self):
        return f"{self.action} on {self.resource_type} #{self.resource_id}"

    def save(self, *args, **kwargs):
        if self.pk:
            raise ValidationError("Audit events are append-only.")
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("Audit events cannot be deleted.")


class NotificationRecord(models.Model):
    user_id = models.IntegerField(db_index=True)
    topic = models.CharField(max_length=80)
    request = models.ForeignKey(
        HRRequest, on_delete=models.PROTECT, related_name="notifications", null=True, blank=True
    )
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "hreis_notification"
        indexes = [
            models.Index(fields=["user_id", "read_at", "created_at"], name="hreis_notify_user_idx"),
        ]

    def __str__(self):
        return f"{self.topic} for user {self.user_id}"
