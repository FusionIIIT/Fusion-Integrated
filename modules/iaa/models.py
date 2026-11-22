"""IAA-owned persistence models; identities remain IAM integer references."""
from django.db import models
from core.db.mixins import TimeStampedModel

class FinancialRecord(TimeStampedModel):
    DRAFT="draft"; SUBMITTED="submitted"; QUERY_RAISED="query_raised"; QUERY_RESPONDED="query_responded"
    FINANCE_VALIDATED="finance_validated"; VERIFIED="verified"; APPROVAL_PENDING="approval_pending"
    ESCALATED="escalated"; ANOMALY_PENDING="anomaly_pending"; APPROVED="approved"
    REJECTED="rejected"; RECORDED="recorded"
    STATUSES=[(DRAFT,"Draft"),(SUBMITTED,"Submitted"),(QUERY_RAISED,"Query Raised"),
      (QUERY_RESPONDED,"Query Responded"),(FINANCE_VALIDATED,"Finance Validated"),(VERIFIED,"Verified"),
      (APPROVAL_PENDING,"Approval Pending"),(ESCALATED,"Escalated"),(ANOMALY_PENDING,"Anomaly Pending"),
      (APPROVED,"Approved"),(REJECTED,"Rejected"),(RECORDED,"Recorded")]
    RECORD_KINDS=[("expense_voucher","Expense / Voucher"),("ta","Travel Allowance")]
    record_kind=models.CharField(max_length=24,choices=RECORD_KINDS,db_index=True)
    request_type=models.CharField(max_length=80); created_by_id=models.IntegerField(db_index=True)
    department=models.CharField(max_length=120,db_index=True); amount=models.DecimalField(max_digits=14,decimal_places=2)
    description=models.TextField(blank=True); status=models.CharField(max_length=24,choices=STATUSES,default=DRAFT,db_index=True)
    financial_year=models.CharField(max_length=12,db_index=True)
    trip_start_date=models.DateField(null=True,blank=True); trip_end_date=models.DateField(null=True,blank=True)
    trip_purpose=models.CharField(max_length=240,blank=True); trip_details=models.JSONField(default=dict,blank=True)
    submitted_at=models.DateTimeField(null=True,blank=True); validated_at=models.DateTimeField(null=True,blank=True)
    recorded_at=models.DateTimeField(null=True,blank=True); current_approval_step=models.PositiveSmallIntegerField(default=0)
    class Meta:
        db_table="iaa_financial_record"; ordering=["-created_at"]
        indexes=[models.Index(fields=["record_kind","status"],name="iaa_record_kind_status_idx"),
          models.Index(fields=["created_by_id","status"],name="iaa_record_creator_status_idx"),
          models.Index(fields=["department","financial_year"],name="iaa_record_dept_year_idx")]
    def __str__(self): return f"{self.record_kind} #{self.pk} ({self.status})"

class ApprovalRule(TimeStampedModel):
    record_kind=models.CharField(max_length=24,blank=True); request_type=models.CharField(max_length=80,blank=True)
    department=models.CharField(max_length=120,blank=True); min_amount=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True)
    max_amount=models.DecimalField(max_digits=14,decimal_places=2,null=True,blank=True); levels=models.JSONField(default=list)
    priority=models.PositiveSmallIntegerField(default=100); is_active=models.BooleanField(default=True)
    class Meta: db_table="iaa_approval_rule"; ordering=["priority","id"]

class DepartmentBudget(TimeStampedModel):
    department=models.CharField(max_length=120); financial_year=models.CharField(max_length=12)
    allocated=models.DecimalField(max_digits=16,decimal_places=2); spent=models.DecimalField(max_digits=16,decimal_places=2,default=0)
    committed=models.DecimalField(max_digits=16,decimal_places=2,default=0); is_active=models.BooleanField(default=True)
    class Meta:
        db_table="iaa_department_budget"
        constraints=[models.UniqueConstraint(fields=("department","financial_year"),name="iaa_budget_dept_year_uniq")]

class FinancialYearPolicy(TimeStampedModel):
    financial_year=models.CharField(max_length=12,unique=True); starts_on=models.DateField()
    ends_on=models.DateField(); settings=models.JSONField(default=dict,blank=True); is_active=models.BooleanField(default=True)
    class Meta: db_table="iaa_financial_year_policy"

class RoleAssignment(TimeStampedModel):
    user_id=models.IntegerField(db_index=True); role=models.CharField(max_length=80,db_index=True)
    assigned_by_id=models.IntegerField(null=True,blank=True); is_active=models.BooleanField(default=True)
    class Meta:
        db_table="iaa_role_assignment"
        constraints=[models.UniqueConstraint(fields=("user_id","role"),name="iaa_role_user_unique")]

class ActiveRoleSelection(TimeStampedModel):
    user_id=models.IntegerField(unique=True); role=models.CharField(max_length=80)
    class Meta: db_table="iaa_active_role_selection"

class AuditObservation(TimeStampedModel):
    OPEN="open"; RESPONDED="responded"; CLOSED="closed"
    STATUSES=[(OPEN,"Open"),(RESPONDED,"Responded"),(CLOSED,"Closed")]
    record_kind=models.CharField(max_length=24); record_id=models.IntegerField(db_index=True)
    department=models.CharField(max_length=120,blank=True); title=models.CharField(max_length=200); details=models.TextField()
    raised_by_id=models.IntegerField(db_index=True); concerned_user_id=models.IntegerField(null=True,blank=True,db_index=True)
    status=models.CharField(max_length=16,choices=STATUSES,default=OPEN,db_index=True)
    verified_by_id=models.IntegerField(null=True,blank=True); verified_at=models.DateTimeField(null=True,blank=True)
    verification_remarks=models.TextField(blank=True); closed_at=models.DateTimeField(null=True,blank=True)
    class Meta: db_table="iaa_audit_observation"; ordering=["-created_at"]
    def delete(self,*args,**kwargs): raise ValueError("IAA audit observations are retained; deletion is prohibited.")

class AuditLogQuerySet(models.QuerySet):
    def update(self,**kwargs): raise ValueError("IAA audit logs are append-only.")
    def delete(self): raise ValueError("IAA audit logs are append-only.")

class AuditLog(models.Model):
    actor_user_id=models.IntegerField(null=True,blank=True,db_index=True); actor_role=models.CharField(max_length=80,blank=True)
    action=models.CharField(max_length=100,db_index=True); resource_type=models.CharField(max_length=60,db_index=True)
    resource_id=models.IntegerField(null=True,blank=True); from_status=models.CharField(max_length=24,blank=True)
    to_status=models.CharField(max_length=24,blank=True); details=models.JSONField(default=dict,blank=True)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True); objects=AuditLogQuerySet.as_manager()
    class Meta: db_table="iaa_audit_log"; ordering=["created_at"]
    def __str__(self):
        return f"{self.action} on {self.resource_type} #{self.resource_id}"

    def save(self,*args,**kwargs):
        if not self._state.adding: raise ValueError("IAA audit logs are append-only.")
        return super().save(*args,**kwargs)

    def delete(self,*args,**kwargs):
        raise ValueError("IAA audit logs are append-only.")

class SupportingDocument(TimeStampedModel):
    uploaded_by_id=models.IntegerField(db_index=True); name=models.CharField(max_length=255)
    storage_reference=models.CharField(max_length=700); content_type=models.CharField(max_length=120,blank=True)
    size_bytes=models.PositiveBigIntegerField(null=True,blank=True)
    record=models.ForeignKey(FinancialRecord,on_delete=models.PROTECT,related_name="attachments")
    class Meta: db_table="iaa_supporting_document"

class FinanceQuery(TimeStampedModel):
    asked_by_id=models.IntegerField(); question=models.TextField()
    status=models.CharField(max_length=16,choices=[("open","Open"),("responded","Responded")],default="open")
    response=models.TextField(blank=True); responded_by_id=models.IntegerField(null=True,blank=True)
    responded_at=models.DateTimeField(null=True,blank=True); record=models.ForeignKey(FinancialRecord,on_delete=models.PROTECT,related_name="queries")
    class Meta: db_table="iaa_finance_query"; ordering=["created_at"]

class ApprovalStep(TimeStampedModel):
    step_number=models.PositiveSmallIntegerField(); authority_role=models.CharField(max_length=80)
    assigned_user_id=models.IntegerField(null=True,blank=True,db_index=True)
    status=models.CharField(max_length=16,choices=[("queued","Queued"),("pending","Pending"),("approved","Approved"),("rejected","Rejected"),("escalated","Escalated")],default="queued",db_index=True)
    timeout_hours=models.PositiveIntegerField(null=True,blank=True); due_at=models.DateTimeField(null=True,blank=True,db_index=True)
    decided_by_id=models.IntegerField(null=True,blank=True); decided_role=models.CharField(max_length=80,blank=True)
    decided_at=models.DateTimeField(null=True,blank=True); remarks=models.TextField(blank=True)
    record=models.ForeignKey(FinancialRecord,on_delete=models.PROTECT,related_name="approval_steps")
    class Meta:
        db_table="iaa_approval_step"; ordering=["step_number"]
        constraints=[models.UniqueConstraint(fields=("record","step_number"),name="iaa_approval_step_unique")]

class Anomaly(TimeStampedModel):
    OPEN="open"; RESOLVED="resolved"; ESCALATED="escalated"
    category=models.CharField(max_length=80,db_index=True); severity=models.CharField(max_length=16,default="medium")
    title=models.CharField(max_length=200); details=models.TextField(blank=True)
    status=models.CharField(max_length=16,choices=[(OPEN,"Open"),(RESOLVED,"Resolved"),(ESCALATED,"Escalated")],default=OPEN,db_index=True)
    raised_by_id=models.IntegerField(null=True,blank=True); resolver_role=models.CharField(max_length=80,blank=True)
    resolver_user_id=models.IntegerField(null=True,blank=True,db_index=True); resolution=models.TextField(blank=True)
    resolved_at=models.DateTimeField(null=True,blank=True); record=models.ForeignKey(FinancialRecord,null=True,blank=True,on_delete=models.PROTECT,related_name="anomalies")
    class Meta: db_table="iaa_anomaly"; ordering=["-created_at"]

class ObservationResponse(TimeStampedModel):
    submitted_by_id=models.IntegerField(); response_text=models.TextField(); evidence_references=models.JSONField(default=list,blank=True)
    observation=models.ForeignKey(AuditObservation,on_delete=models.PROTECT,related_name="responses")
    class Meta: db_table="iaa_observation_response"; ordering=["created_at"]

class DashboardNotification(models.Model):
    recipient_user_id=models.IntegerField(db_index=True); recipient_role=models.CharField(max_length=80,blank=True)
    event_type=models.CharField(max_length=80,db_index=True); title=models.CharField(max_length=180)
    message=models.TextField(blank=True); resource_type=models.CharField(max_length=60,blank=True)
    resource_id=models.IntegerField(null=True,blank=True); read_at=models.DateTimeField(null=True,blank=True)
    created_at=models.DateTimeField(auto_now_add=True,db_index=True)
    class Meta: db_table="iaa_dashboard_notification"; ordering=["-created_at"]

    def __str__(self):
        return f"{self.title} for user {self.recipient_user_id}"
