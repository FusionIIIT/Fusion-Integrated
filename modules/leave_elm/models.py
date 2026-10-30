from django.db import models
from django.utils import timezone
from core.db.mixins import TimeStampedModel, UserScopedModel

class LeaveCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class LeaveType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class LeaveApplication(TimeStampedModel, UserScopedModel):
    leave_type = models.ForeignKey(LeaveType, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    status = models.CharField(max_length=50, default='Pending')
    approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='approved_by_applications')
    approved_at = models.DateTimeField(null=True, blank=True)
    cancelled_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='cancelled_by_applications')
    cancelled_at = models.DateTimeField(null=True, blank=True)
    extension_requested = models.BooleanField(default=False)
    extension_approved = models.BooleanField(default=False)
    extension_start_date = models.DateField(null=True, blank=True)
    extension_end_date = models.DateField(null=True, blank=True)
    extension_approved_by = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL, related_name='extension_approved_by_applications')
    extension_approved_at = models.DateTimeField(null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.status == 'Approved' and not self.approved_at:
            self.approved_at = timezone.now()
        if self.status == 'Cancelled' and not self.cancelled_at:
            self.cancelled_at = timezone.now()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Application {self.id} for {self.leave_type.name} from {self.start_date} to {self.end_date}'


class LeaveBalance(TimeStampedModel, UserScopedModel):
    user_id = models.IntegerField(db_index=True)
    leave_category = models.ForeignKey(LeaveCategory, on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=5, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    def __str__(self):
        return f'Leave Balance for {self.user_id} in {self.leave_category.name}'


class LeavePolicy(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    cl_days = models.IntegerField(default=8)
    rh_days = models.IntegerField(default=2)
    scl_days = models.IntegerField(default=15)
    el_days = models.IntegerField(default=30)
    col_days = models.IntegerField(default=20)
    vl_days = models.IntegerField(default=60)

    def __str__(self):
        return self.name


class LeaveHistory(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    status = models.CharField(max_length=50)
    decision = models.TextField(blank=True)

    def __str__(self):
        return f'Leave History {self.id} for {self.leave_application.id}'


class LeaveNotification(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    message = models.TextField()

    def __str__(self):
        return f'Leave Notification {self.id} for {self.leave_application.id}'


class LeaveTask(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    task_type = models.CharField(max_length=50)
    status = models.CharField(max_length=50)
    reminder_threshold = models.IntegerField(default=60)
    escalation_threshold = models.IntegerField(default=120)

    def __str__(self):
        return f'Leave Task {self.id} for {self.leave_application.id}'


class LeaveSubstitution(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    substitute_user_id = models.IntegerField(db_index=True)

    def __str__(self):
        return f'Leave Substitution {self.id} for {self.leave_application.id}'


class LeaveExtension(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    extension_start_date = models.DateField()
    extension_end_date = models.DateField()

    def __str__(self):
        return f'Leave Extension {self.id} for {self.leave_application.id}'


class LeaveResumption(TimeStampedModel, UserScopedModel):
    leave_application = models.ForeignKey(LeaveApplication, on_delete=models.CASCADE)
    actual_resumption_date = models.DateField()

    def __str__(self):
        return f'Leave Resumption {self.id} for {self.leave_application.id}'


class LeavePolicyParameter(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    value = models.JSONField()

    def __str__(self):
        return self.name


class LeaveCalendar(TimeStampedModel, UserScopedModel):
    name = models.CharField(max_length=100, unique=True)
    holidays = models.JSONField()

    def __str__(self):
        return self.name