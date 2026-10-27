from django.db import models

LEAVE_TYPES = (
    ('CL', 'Casual Leave'),
    ('RH', 'Restricted Holiday'),
    ('SCL', 'Special Casual Leave'),
    ('EL', 'Earned Leave'),
    ('COL', 'Commuted Leave'),
    ('VL', 'Vacation Leave'),
)

SUBSTITUTE_STATUS = (
    ('none', 'None'),
    ('pending', 'Pending'),
    ('accepted', 'Accepted'),
    ('declined', 'Declined'),
)

STATUS = (
    ('pending', 'Pending'),
    ('approved', 'Approved'),
    ('rejected', 'Rejected'),
    ('withdrawn', 'Withdrawn'),
    ('cancellation_requested', 'Cancellation Requested'),
    ('cancelled', 'Cancelled'),
)

CURRENT_STAGE = (
    ('substitute_consent', 'Substitute Consent'),
    ('unit_head_review', 'Unit Head Review'),
    ('establishment_review', 'Establishment Review'),
    ('final_sanction', 'Final Sanction'),
    ('completed', 'Completed'),
)

TRANSACTION_TYPES = (
    ('credit', 'Credit'),
    ('debit', 'Debit'),
    ('restoration', 'Restoration'),
    ('lapse', 'Lapse'),
    ('vl_conversion', 'VL Conversion'),
)


class LeaveRequest(models.Model):
    user_id = models.PositiveBigIntegerField(db_index=True)
    category = models.CharField(max_length=3, choices=LEAVE_TYPES)
    start_date = models.DateField()
    end_date = models.DateField()
    part_of_day = models.CharField(max_length=10, default='full')
    days_requested = models.DecimalField(max_digits=5, decimal_places=2, default=1.0)
    reason = models.TextField()
    station_leave = models.BooleanField(default=False)
    station_destination = models.CharField(max_length=200, blank=True)
    substitute_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    substitute_status = models.CharField(max_length=16, choices=SUBSTITUTE_STATUS, default='none')
    status = models.CharField(max_length=24, choices=STATUS)
    current_stage = models.CharField(max_length=32, choices=CURRENT_STAGE, default='unit_head_review')
    is_extension = models.BooleanField(default=False)
    parent_request = models.ForeignKey('self', null=True, blank=True, on_delete=models.SET_NULL)
    resumption_date = models.DateField(null=True, blank=True)
    resumption_status = models.CharField(max_length=16, default='none')
    offline_sanctioned = models.BooleanField(default=False)
    offline_reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class LeaveBalance(models.Model):
    user_id = models.PositiveBigIntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=LEAVE_TYPES)
    entitled_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    used_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)
    carried_forward_days = models.DecimalField(max_digits=6, decimal_places=2, default=0)

    class Meta:
        unique_together = ('user_id', 'year', 'category')

    @property
    def available_days(self):
        return self.entitled_days + self.carried_forward_days - self.used_days


class LeaveTransaction(models.Model):
    request = models.ForeignKey(LeaveRequest, null=True, blank=True, on_delete=models.CASCADE, related_name='transactions')
    user_id = models.PositiveBigIntegerField()
    year = models.PositiveSmallIntegerField()
    category = models.CharField(max_length=3, choices=LEAVE_TYPES)
    transaction_type = models.CharField(max_length=16, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=6, decimal_places=2)
    note = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)


class HolidayCalendar(models.Model):
    date = models.DateField(unique=True)
    name = models.CharField(max_length=100)
    is_restricted = models.BooleanField(default=False)
    year = models.PositiveSmallIntegerField()


class LeaveAction(models.Model):
    request = models.ForeignKey(LeaveRequest, on_delete=models.CASCADE, related_name='actions')
    actor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    action = models.CharField(max_length=32)
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)