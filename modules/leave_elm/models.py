
from decimal import Decimal
from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    working_days = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('1.00'))
    station_leave_required = models.BooleanField(default=False)
    address_during_leave = models.TextField(blank=True, default='')
    contact_number = models.CharField(max_length=32, blank=True, default='')
    academic_substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    admin_substitute_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    attachment_reference = models.CharField(max_length=255, blank=True, default='')
    remarks = models.TextField(blank=True, default='')
    reviewed_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    balance_deducted = models.BooleanField(default=False)
    resumed_at = models.DateTimeField(null=True, blank=True)
    fitness_certificate_reference = models.CharField(max_length=255, blank=True, default='')
    approved_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by_id = models.IntegerField(null=True, blank=True, db_index=True)
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    @property
    def approved_by(self):
        return self.approved_by_id

    @approved_by.setter
    def approved_by(self, value):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        self.approved_by_id = value

    @property
    def cancelled_by(self):
        return self.cancelled_by_id

    @cancelled_by.setter
    def cancelled_by(self, value):
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        self.cancelled_by_id = value

    @property
    def extension_approved_by(self):
        return self.extension_approved_by_id

    @extension_approved_by.setter
    def extension_approved_by(self, value):
        if self.extension_approved:
            self.extension_approved_at = timezone.now()
        self.extension_approved_by_id = value

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.status in ['Approved', 'Cancelled']:
            setattr(self, f'{self.status}_at', timezone.now())

class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)
    action = models.CharField(max_length=64, blank=True, default='')

class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    channel = models.CharField(max_length=32, default='in_app')

class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)
    role = models.CharField(max_length=64, blank=True, default='reviewer')
    reminded_at = models.DateTimeField(null=True, blank=True)
    escalated_at = models.DateTimeField(null=True, blank=True)

class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)
    substitution_type = models.CharField(max_length=32, default='academic')
    status = models.CharField(max_length=32, default='Pending')
    remarks = models.TextField(blank=True, default='')
    responded_at = models.DateTimeField(null=True, blank=True)

class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()
    reason = models.TextField(blank=True, default='')
    status = models.CharField(max_length=32, default='Pending')

class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()
    remarks = models.TextField(blank=True, default='')
    fitness_certificate_reference = models.CharField(max_length=255, blank=True, default='')
    status = models.CharField(max_length=32, default='Submitted')

class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField(default=dict)

class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField(default=list)
