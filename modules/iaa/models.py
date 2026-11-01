"""ORM only. No business logic. No cross-module ForeignKey — user refs are plain ids."""
from django.db import models


class RequestStatus(models.TextChoices):
    DRAFT = 'DRAFT', 'Draft'
    SUBMITTED = 'SUBMITTED', 'Submitted'
    QUERY_RAISED = 'QUERY_RAISED', 'Query Raised'
    FINANCE_VALIDATED = 'FINANCE_VALIDATED', 'Finance Validated'
    APPROVAL_PENDING = 'APPROVAL_PENDING', 'Approval Pending'
    ESCALATED = 'ESCALATED', 'Escalated'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    RECORDED = 'RECORDED', 'Recorded'


class TaStatus(models.TextChoices):
    SUBMITTED = 'SUBMITTED', 'Submitted'
    QUERY_RAISED = 'QUERY_RAISED', 'Query Raised'
    VERIFIED = 'VERIFIED', 'Verified'
    APPROVAL_PENDING = 'APPROVAL_PENDING', 'Approval Pending'
    ESCALATED = 'ESCALATED', 'Escalated'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    RECORDED = 'RECORDED', 'Recorded'


class AnomalyStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    RESOLVED = 'RESOLVED', 'Resolved'
    ESCALATED = 'ESCALATED', 'Escalated'


class ObservationStatus(models.TextChoices):
    OPEN = 'OPEN', 'Open'
    RESPONDED = 'RESPONDED', 'Responded'
    CLOSED = 'CLOSED', 'Closed'


class ExpenseVoucherRequest(models.Model):
    creator_id = models.IntegerField()
    request_type = models.CharField(max_length=50)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    department = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=RequestStatus.choices,
                               default=RequestStatus.DRAFT)
    approval_level = models.PositiveSmallIntegerField(default=0)
    approval_levels_required = models.PositiveSmallIntegerField(default=1)
    current_approver_id = models.IntegerField(null=True, blank=True)
    query_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class TAClaim(models.Model):
    employee_id = models.IntegerField()
    trip_start = models.DateField()
    trip_end = models.DateField()
    purpose = models.TextField()
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, choices=TaStatus.choices,
                               default=TaStatus.SUBMITTED)
    is_high_value = models.BooleanField(default=False)
    approval_level = models.PositiveSmallIntegerField(default=0)
    approval_levels_required = models.PositiveSmallIntegerField(default=1)
    current_approver_id = models.IntegerField(null=True, blank=True)
    query_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class ApprovalDecision(models.Model):
    expense_request = models.ForeignKey(ExpenseVoucherRequest, null=True, blank=True,
                                         on_delete=models.CASCADE, related_name='decisions')
    ta_claim = models.ForeignKey(TAClaim, null=True, blank=True,
                                  on_delete=models.CASCADE, related_name='decisions')
    approver_id = models.IntegerField()
    decision = models.CharField(max_length=10,
                                 choices=[('APPROVED', 'Approved'), ('REJECTED', 'Rejected')])
    remarks = models.TextField()
    level = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)


class Anomaly(models.Model):
    expense_request = models.ForeignKey(ExpenseVoucherRequest, null=True, blank=True,
                                         on_delete=models.CASCADE, related_name='anomalies')
    ta_claim = models.ForeignKey(TAClaim, null=True, blank=True,
                                  on_delete=models.CASCADE, related_name='anomalies')
    category = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=AnomalyStatus.choices,
                               default=AnomalyStatus.OPEN)
    resolver_id = models.IntegerField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditObservation(models.Model):
    expense_request = models.ForeignKey(ExpenseVoucherRequest, null=True, blank=True,
                                         on_delete=models.CASCADE, related_name='observations')
    ta_claim = models.ForeignKey(TAClaim, null=True, blank=True,
                                  on_delete=models.CASCADE, related_name='observations')
    auditor_id = models.IntegerField()
    description = models.TextField()
    status = models.CharField(max_length=20, choices=ObservationStatus.choices,
                               default=ObservationStatus.OPEN)
    response_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class AuditLogEntry(models.Model):
    user_id = models.IntegerField()
    active_role = models.CharField(max_length=50)
    action = models.CharField(max_length=100)
    resulting_status = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
