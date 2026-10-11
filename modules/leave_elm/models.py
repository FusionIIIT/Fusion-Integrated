from django.db import models

class LeaveRequest(models.Model):
    employee_id = models.CharField(max_length=100)
    category = models.CharField(choices=[('CL', 'Casual Leave'), ('RH', 'Regular Holiday'), ('SCL', 'Special Category Leave'), ('EL', 'Emergency Leave'), ('COL', 'Compensatory Leave'), ('VL', 'Voluntary Leave')], max_length=3)
    start_date = models.DateField()
    end_date = models.DateField()
    purpose = models.TextField()
    station_leave = models.BooleanField(default=False)
    half_day = models.BooleanField(default=False)
    substitute_employee_id = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(choices=[('P', 'Pending'), ('A', 'Approved'), ('R', 'Rejected')], max_length=1)
    requested_days = models.DecimalField(decimal_places=2, max_digits=5)
    timestamps = models.DateTimeField(auto_now_add=True)
    current_approver_id = models.CharField(max_length=100, blank=True, null=True)
    decision_note = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamps']
        indexes = [
            models.Index(fields=['employee_id', 'category', 'start_date']),
            models.Index(fields=['status'])
        ]

class LeaveAction(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE)
    actor_id = models.CharField(max_length=100)
    action = models.CharField(choices=[('A', 'Approved'), ('R', 'Rejected'), ('C', 'Commented')], max_length=1)
    from_status = models.CharField(max_length=1)
    to_status = models.CharField(max_length=1)
    comment = models.TextField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']

class LeaveBalance(models.Model):
    employee_id = models.CharField(max_length=100)
    year = models.IntegerField()
    category = models.CharField(choices=[('CL', 'Casual Leave'), ('RH', 'Regular Holiday'), ('SCL', 'Special Category Leave'), ('EL', 'Emergency Leave'), ('COL', 'Compensatory Leave'), ('VL', 'Voluntary Leave')], max_length=3)
    opening = models.DecimalField(decimal_places=2, max_digits=5)
    credited = models.DecimalField(decimal_places=2, max_digits=5)
    used = models.DecimalField(decimal_places=2, max_digits=5)
    closing = models.DecimalField(decimal_places=2, max_digits=5)

    class Meta:
        ordering = ['-year']

class LeaveTransaction(models.Model):
    employee_id = models.CharField(max_length=100, blank=True, null=True)
    category = models.CharField(choices=[('CL', 'Casual Leave'), ('RH', 'Regular Holiday'), ('SCL', 'Special Category Leave'), ('EL', 'Emergency Leave'), ('COL', 'Compensatory Leave'), ('VL', 'Voluntary Leave')], max_length=3, blank=True, null=True)
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, blank=True, null=True)
    transaction_type = models.CharField(choices=[('I', 'Input'), ('O', 'Output')], max_length=1)
    amount = models.DecimalField(decimal_places=2, max_digits=5)
    effective_date = models.DateField()
    reference = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-effective_date']

class Holiday(models.Model):
    date = models.DateField()
    name = models.CharField(max_length=100)
    restricted_holiday = models.BooleanField(default=False)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['date']

class VacationPeriod(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    name = models.CharField(max_length=100)
    published = models.BooleanField(default=True)

    class Meta:
        ordering = ['start_date']

class LeaveConfiguration(models.Model):
    key = models.CharField(max_length=100)
    value = models.TextField()

    class Meta:
        ordering = ['key']
