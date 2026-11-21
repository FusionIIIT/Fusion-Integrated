from django.db import models
from decimal import Decimal
from modules.directory.models import UserRef

ANNUAL_ENTITLEMENT = {
    'CL': 8,
    'RH': 2,
    'SCL': 15
}

class LeaveType(models.TextChoices):
    CL = 'CL', 'Casual Leave'
    RH = 'RH', 'Restricted Holiday'
    SCL = 'SCL', 'Special Casual Leave'

class LeaveBalance(models.Model):
    user = models.ForeignKey(UserRef, on_delete=models.PROTECT)
    year = models.IntegerField()
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    entitled = models.DecimalField(max_digits=4, decimal_places=1)
    used = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    lapsed = models.DecimalField(max_digits=4, decimal_places=1, default=0)

    class Meta:
        unique_together = ('user', 'year', 'leave_type')

class RestrictedHoliday(models.Model):
    year = models.IntegerField()
    date = models.DateField(unique=True)
    name = models.CharField(max_length=255)
    is_published = models.BooleanField(default=False)

class LeaveApplicationStatus(models.TextChoices):
    PENDING = 'PENDING', 'Pending'
    APPROVED = 'APPROVED', 'Approved'
    REJECTED = 'REJECTED', 'Rejected'
    WITHDRAWN = 'WITHDRAWN', 'Withdrawn'
    CANCELLED = 'CANCELLED', 'Cancelled'

class LeaveApplication(models.Model):
    user = models.ForeignKey(UserRef, on_delete=models.PROTECT)
    leave_type = models.CharField(max_length=3, choices=LeaveType.choices)
    start_date = models.DateField()
    end_date = models.DateField()
    half_day = models.CharField(
        max_length=10,
        choices=[
            ('NONE', 'None'),
            ('FIRST', 'First Half'),
            ('SECOND', 'Second Half')
        ],
        default='NONE'
    )
    days = models.DecimalField(max_digits=4, decimal_places=1)
    special_purpose = models.TextField(blank=True)
    special_purpose_admissible = models.BooleanField(default=False)
    status = models.CharField(
        max_length=10,
        choices=LeaveApplicationStatus.choices,
        default='PENDING'
    )
    created_at = models.DateTimeField(auto_now_add=True)

class LeaveTransaction(models.Model):
    balance = models.ForeignKey(LeaveBalance, on_delete=models.CASCADE)
    application = models.ForeignKey(LeaveApplication, on_delete=models.SET_NULL, null=True)
    kind = models.CharField(
        max_length=10,
        choices=[
            ('DEDUCT', 'Deduct'),
            ('LAPSE', 'Lapse')
        ]
    )
    days = models.DecimalField(max_digits=4, decimal_places=1)
    created_at = models.DateTimeField(auto_now_add=True)
