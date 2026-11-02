from django.db import models

class ExpenseRequest(models.Model):
    creator_user_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=200)
    description = models.TextField()
    request_type = models.CharField(max_length=32, choices=[('reimbursement', 'Reimbursement'), ('advance', 'Advance'), ('vendor_payment', 'Vendor Payment'), ('petty_cash', 'Petty Cash')])
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=32, choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('under_finance_review', 'Under Finance Review'), ('clarification_requested', 'Clarification Requested'), ('clarification_responded', 'Clarification Responded'), ('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('escalated', 'Escalated'), ('internal_completed', 'Internal Completed')], default='draft')
    current_authority_role = models.CharField(max_length=32, default='none', choices=[('none', 'None'), ('finance', 'Finance Staff'), ('hod', 'Head of Department'), ('dean', 'Dean'), ('director', 'Director')])
    current_authority_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    clarification_query = models.TextField(blank=True)
    clarification_response = models.TextField(blank=True)
    submission_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class TravelAllowanceClaim(models.Model):
    claimant_user_id = models.PositiveBigIntegerField(db_index=True)
    department = models.CharField(max_length=64, db_index=True)
    purpose = models.CharField(max_length=255)
    departure_place = models.CharField(max_length=100)
    destination_place = models.CharField(max_length=100)
    start_date = models.DateField()
    end_date = models.DateField()
    claimed_amount = models.DecimalField(max_digits=12, decimal_places=2)
    approved_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    is_high_value = models.BooleanField(default=False)
    status = models.CharField(max_length=32, choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('under_finance_review', 'Under Finance Review'), ('clarification_requested', 'Clarification Requested'), ('clarification_responded', 'Clarification Responded'), ('pending_approval', 'Pending Approval'), ('approved', 'Approved'), ('rejected', 'Rejected'), ('escalated', 'Escalated'), ('internal_completed', 'Internal Completed')], default='draft')
    current_authority_role = models.CharField(max_length=32, default='none')
    current_authority_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class DepartmentBudget(models.Model):
    department = models.CharField(max_length=64, unique=True)
    financial_year = models.CharField(max_length=10, default='2026-27')
    allocated_amount = models.DecimalField(max_digits=14, decimal_places=2)
    committed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)
    spent_amount = models.DecimalField(max_digits=14, decimal_places=2, default=0.0)

    @property
    def available_budget(self):
        return self.allocated_amount - self.committed_amount - self.spent_amount

class AnomalyRecord(models.Model):
    anomaly_category = models.CharField(max_length=32, choices=[('budget_insufficiency', 'Budget Insufficiency'), ('policy_violation', 'Policy Violation'), ('documentation_gap', 'Documentation Gap'), ('high_value_escalation', 'High Value Escalation')])
    severity = models.CharField(max_length=16, choices=[('low', 'Low'), ('medium', 'Medium'), ('high', 'High'), ('critical', 'Critical')], default='medium')
    description = models.TextField()
    related_expense = models.ForeignKey(ExpenseRequest, null=True, blank=True, on_delete=models.SET_NULL, related_name='anomalies')
    related_ta = models.ForeignKey(TravelAllowanceClaim, null=True, blank=True, on_delete=models.SET_NULL, related_name='anomalies')
    flagged_by_role = models.CharField(max_length=32, default='finance')
    flagged_by_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    status = models.CharField(max_length=16, choices=[('open', 'Open'), ('resolved', 'Resolved'), ('escalated', 'Escalated')], default='open')
    resolution_remarks = models.TextField(blank=True)
    resolver_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class AuditObservation(models.Model):
    observation_code = models.CharField(max_length=32, unique=True)
    auditor_user_id = models.PositiveBigIntegerField(db_index=True)
    target_department = models.CharField(max_length=64, db_index=True)
    subject = models.CharField(max_length=200)
    query_details = models.TextField()
    department_response = models.TextField(blank=True)
    status = models.CharField(max_length=32, choices=[('draft', 'Draft'), ('raised', 'Raised'), ('response_submitted', 'Response Submitted'), ('verified_closed', 'Verified Closed'), ('escalated', 'Escalated')], default='draft')
    verified_by_auditor = models.BooleanField(default=False)
    closure_remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ApprovalAction(models.Model):
    entity_type = models.CharField(max_length=32, choices=[('expense', 'Expense Request'), ('ta', 'TA Claim'), ('anomaly', 'Anomaly Record'), ('audit', 'Audit Observation')])
    entity_id = models.PositiveBigIntegerField(db_index=True)
    actor_user_id = models.PositiveBigIntegerField(db_index=True)
    actor_role = models.CharField(max_length=32)
    action = models.CharField(max_length=64)
    remarks = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)