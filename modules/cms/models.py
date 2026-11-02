from django.db import models
from django.utils import timezone
import uuid

class Complaint(models.Model):
    complaint_id = models.CharField(max_length=50, unique=True, db_index=True)
    complainant_user_id = models.PositiveBigIntegerField(db_index=True)
    CATEGORY_CHOICES = [
        ('hostel', 'Hostel'),
        ('academic', 'Academic'),
        ('maintenance', 'Maintenance'),
        ('network', 'Network'),
        ('mess', 'Mess'),
        ('other', 'Other'),
    ]
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    description = models.TextField()
    submission_timestamp = models.DateTimeField(default=timezone.now)
    PRIORITY_CHOICES = [
        ('Low', 'Low'),
        ('Medium', 'Medium'),
        ('High', 'High'),
    ]
    priority = models.CharField(max_length=50, choices=PRIORITY_CHOICES, default='Low')
    assigned_handler_id = models.PositiveBigIntegerField(null=True, blank=True)
    STATUS_CHOICES = [
        ('Submitted', 'Submitted'),
        ('In Progress', 'In Progress'),
        ('Resolved', 'Resolved'),
        ('Rejected', 'Rejected'),
        ('Closed', 'Closed'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Submitted')
    resolution_details = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    requires_supervisor_verification = models.BooleanField(default=False)
    user_verified = models.BooleanField(default=False)
    supervisor_verified = models.BooleanField(default=False)
    closure_timestamp = models.DateTimeField(null=True, blank=True)
    is_escalated = models.BooleanField(default=False)
    ESCALATION_TYPE_CHOICES = [
        ('none', 'None'),
        ('manual', 'Manual'),
        ('automatic_sla', 'Automatic SLA'),
    ]
    escalation_type = models.CharField(max_length=50, choices=ESCALATION_TYPE_CHOICES, default='none')
    escalation_timestamp = models.DateTimeField(null=True, blank=True)
    escalation_remarks = models.TextField(blank=True)
    sla_due_date = models.DateTimeField(null=True, blank=True)
    sla_reminder_sent = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @classmethod
    def generate_unique_complaint_id(cls):
        return f"CMS-2026-{uuid.uuid4().hex[:8].upper()}"

    def __str__(self):
        return f"{self.complaint_id} ({self.status})"

class ComplaintAttachment(models.Model):
    complaint = models.ForeignKey(Complaint, related_name='attachments', on_delete=models.CASCADE)
    file_name = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()
    file_type = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file_name} ({self.complaint_id})"

class ComplaintProgress(models.Model):
    complaint = models.ForeignKey(Complaint, related_name='progress_history', on_delete=models.CASCADE)
    actor_user_id = models.PositiveBigIntegerField()
    actor_role = models.CharField(max_length=255, default='handler')
    action = models.CharField(max_length=255, default='update')
    remarks = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.action} on {self.complaint.complaint_id}"

class ComplaintReopening(models.Model):
    complaint = models.ForeignKey(Complaint, related_name='reopenings', on_delete=models.CASCADE)
    complainant_user_id = models.PositiveBigIntegerField()
    dissatisfaction_reason = models.TextField()
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('denied', 'Denied'),
    ]
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='pending')
    supervisor_user_id = models.PositiveBigIntegerField(null=True, blank=True)
    supervisor_remarks = models.TextField(blank=True)
    requested_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Reopening {self.status} for {self.complaint.complaint_id}"

class ComplaintFeedback(models.Model):
    complaint = models.ForeignKey(Complaint, related_name='feedbacks', on_delete=models.CASCADE)
    complainant_user_id = models.PositiveBigIntegerField()
    rating = models.PositiveSmallIntegerField(choices=[(1, '1'), (2, '2'), (3, '3'), (4, '4'), (5, '5')])
    comments = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Feedback {self.rating}/5 for {self.complaint.complaint_id}"

class ComplaintAnnouncement(models.Model):
    author_user_id = models.PositiveBigIntegerField()
    author_role = models.CharField(max_length=255)
    title = models.CharField(max_length=255)
    content = models.TextField()
    is_active = models.BooleanField(default=True)
    published_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title

class CmsRoleAssignment(models.Model):
    user_id = models.PositiveBigIntegerField()
    ROLE_CHOICES = [
        ('complaint_handler', 'Complaint Handler'),
        ('complaint_supervisor', 'Complaint Supervisor'),
    ]
    role_type = models.CharField(max_length=50, choices=ROLE_CHOICES)
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=True)
    assigned_by_id = models.PositiveBigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.role_type} - User {self.user_id}"
