from django.db import models
from django.utils.translation import gettext_lazy as _

class LeaveType(models.TextChoices):
    CASUAL = 'CASUAL', _('Casual Leave')
    MEDICAL = 'MEDICAL', _('Medical Leave')
    ACADEMIC = 'ACADEMIC', _('Academic Leave')

class RequestStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')

class DepartmentChoice(models.TextChoices):
    LIBRARY = 'LIBRARY', _('Library')
    HOSTEL = 'HOSTEL', _('Hostel')
    MESS = 'MESS', _('Mess')
    SPORTS = 'SPORTS', _('Sports')
    COMPUTER_CENTER = 'COMPUTER_CENTER', _('Computer Center')
    LAB = 'LAB', _('Department Lab')
    ACCOUNTS = 'ACCOUNTS', _('Accounts')

class ClearanceStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    CLEARED = 'CLEARED', _('Cleared')
    DUES_OUTSTANDING = 'DUES_OUTSTANDING', _('Dues Outstanding')

class SeminarStatus(models.TextChoices):
    SCHEDULED = 'SCHEDULED', _('Scheduled')
    COMPLETED = 'COMPLETED', _('Completed')
    CANCELLED = 'CANCELLED', _('Cancelled')

class StudentLeaveRequest(models.Model):
    student_id = models.CharField(max_length=50)
    student_name = models.CharField(max_length=150)
    leave_type = models.CharField(max_length=30, choices=LeaveType.choices, default=LeaveType.CASUAL)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.TextField()
    status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    hod_remarks = models.TextField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class BonafideRequest(models.Model):
    student_id = models.CharField(max_length=50)
    purpose = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    certificate_number = models.CharField(max_length=100, blank=True, default='')
    issued_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

class NoDuesClearance(models.Model):
    student_id = models.CharField(max_length=50)
    program = models.CharField(max_length=50)
    is_finalized = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class NoDuesItem(models.Model):
    clearance = models.ForeignKey(NoDuesClearance, related_name='items', on_delete=models.CASCADE)
    department = models.CharField(max_length=50, choices=DepartmentChoice.choices)
    status = models.CharField(max_length=30, choices=ClearanceStatus.choices, default=ClearanceStatus.PENDING)
    remarks = models.TextField(blank=True, default='')
    cleared_by = models.CharField(max_length=50, blank=True, default='')
    updated_at = models.DateTimeField(auto_now=True)

class PGAssistantshipClaim(models.Model):
    student_id = models.CharField(max_length=50)
    month_year = models.CharField(max_length=20)
    hours_rendered = models.PositiveIntegerField(default=0)
    thesis_supervisor_status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    ta_supervisor_status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    dept_admin_forwarded = models.BooleanField(default=False)
    hod_status = models.CharField(max_length=30, choices=RequestStatus.choices, default=RequestStatus.PENDING)
    stipend_processed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

class GraduateSeminar(models.Model):
    student_id = models.CharField(max_length=50)
    seminar_title = models.CharField(max_length=255)
    scheduled_date = models.DateField()
    time_slot = models.CharField(max_length=50)
    venue = models.CharField(max_length=150)
    scheduled_by = models.CharField(max_length=50)
    status = models.CharField(max_length=30, choices=SeminarStatus.choices, default=SeminarStatus.SCHEDULED)
    created_at = models.DateTimeField(auto_now_add=True)