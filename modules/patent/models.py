from django.db import models
from core.db.mixins import TimeStampedModel


class PatentApplication(TimeStampedModel):
    """Core patent application record."""
    
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("under_review", "Under Review"),
        ("needs_revision", "Needs Revision"),
        ("resubmitted", "Resubmitted"),
        ("rejected", "Rejected"),
        ("appeal_submitted", "Appeal Submitted"),
        ("approved", "Approved"),
        ("attorney_assigned", "Attorney Assigned"),
        ("filed", "Filed"),
        ("granted", "Granted"),
        ("withdrawn", "Withdrawn"),
        ("expired", "Expired"),
    ]

    APPLICATION_NUMBER = models.CharField(max_length=20, unique=True)
    title = models.CharField(max_length=255)
    abstract = models.TextField(blank=True)
    description = models.TextField()
    claims = models.TextField()
    technical_domain = models.CharField(max_length=100)
    
    applicant_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="draft")
    assigned_director_id = models.IntegerField(null=True, blank=True)
    assigned_attorney_id = models.IntegerField(null=True, blank=True)
    review_due_date = models.DateField(null=True, blank=True)
    resubmission_deadline = models.DateField(null=True, blank=True)
    
    # Latest decision and justification (stored as text for flexibility)
    latest_decision = models.CharField(max_length=50, null=True, blank=True)
    latest_justification = models.TextField(blank=True)
    
    version_number = models.IntegerField(default=1)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION_NUMBER} ({self.status})"


class Inventor(TimeStampedModel):
    """Inventor associated with a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="inventors")
    user_id = models.IntegerField(null=True, blank=True, db_index=True)  # Optional: linked IAM user
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True)
    contribution_percent = models.DecimalField(max_digits=5, decimal_places=1, default=0.0)
    agreement_signed = models.BooleanField(default=False)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION", "user_id"]  # Prevent duplicate entries for same user

    def __str__(self):
        return f"Inventor {self.name} on {self.APPLICATION}"


class ApplicationDocument(TimeStampedModel):
    """Document associated with a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="documents")
    file_name = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)  # e.g., "application.pdf"
    size = models.BigIntegerField()  # in bytes
    version = models.IntegerField(default=1)
    sensitivity = models.CharField(max_length=20, choices=[("public", "Public"), ("internal", "Internal"), ("confidential", "Confidential")])
    uploaded_by = models.IntegerField(db_index=True)
    archived = models.BooleanField(default=False)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.file_name} (v{self.version})"


class AttorneyAssignment(TimeStampedModel):
    """Attorney assignment record for a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="assignments")
    attorney_id = models.IntegerField(db_index=True)
    status = models.CharField(max_length=20, choices=[("offered", "Offered"), ("accepted", "Accepted"), ("declined", "Declined")], default="offered")
    decline_reason = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One assignment per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - {self.attorney_id} ({self.status})"


class PatentabilityOpinion(TimeStampedModel):
    """Attorney's legal and patentability assessment."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="opinions")
    attorney_id = models.IntegerField(db_index=True)
    novelty = models.BooleanField(default=False)  # True if novel
    non_obviousness = models.BooleanField(default=False)  # True if non-obvious
    utility = models.BooleanField(default=False)  # True if useful
    recommendation = models.CharField(max_length=30, choices=[("file_patent", "File Patent"), ("do_not_file", "Do Not File"), ("needs_amendment", "Needs Amendment")], default="needs_amendment")
    opinion_text = models.TextField()

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One primary opinion per application

    def __str__(self):
        return f"{self.APPLICATION} - {self.recommendation}"


class Budget(TimeStampedModel):
    """Budget record for a patent application."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="budgets")
    filing_fee = models.DecimalField(max_digits=10, decimal_places=2)
    attorney_fee = models.DecimalField(max_digits=10, decimal_places=2)
    administrative_cost = models.DecimalField(max_digits=10, decimal_places=2)
    total = models.DecimalField(max_digits=10, decimal_places=2)  # Calculated field (can be overridden by manager)
    status = models.CharField(max_length=20, choices=[("pending", "Pending"), ("approved", "Approved"), ("rejected", "Rejected"), ("escalated", "Escalated")], default="pending")
    decided_by = models.IntegerField(null=True, blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One budget per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - ${self.total}"


class Filing(TimeStampedModel):
    """External patent office filing record."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="filings")
    patent_office = models.CharField(max_length=100)  # e.g., "USPTO", "EPO"
    filing_number = models.CharField(max_length=50)
    filing_date = models.DateField()
    international = models.BooleanField(default=False)
    grant_number = models.CharField(max_length=50, null=True, blank=True)
    grant_date = models.DateField(null=True, blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One primary filing per application

    def __str__(self):
        return f"{self.APPLICATION} - {self.patent_office} #{self.filing_number}"


class OfficeAction(TimeStampedModel):
    """Office action received from patent office."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="office_actions")
    received_date = models.DateField()
    response_due_date = models.DateField(null=True, blank=True)
    description = models.TextField()
    response_text = models.TextField(blank=True)  # Draft or submitted response
    status = models.CharField(max_length=30, choices=[("recorded", "Recorded"), ("awaiting_applicant_approval", "Awaiting Applicant Approval"), ("applicant_approved", "Applicant Approved"), ("response_ready", "Response Ready"), ("response_submitted", "Response Submitted")], default="recorded")

    class Meta:
        app_label = "patent"
        ordering = ["-received_date"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.status}"


class MaintenanceRecord(TimeStampedModel):
    """Maintenance fee renewal record."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="maintenance_records")
    due_date = models.DateField()
    fee = models.DecimalField(max_digits=10, decimal_places=2)
    decision = models.CharField(max_length=30, choices=[("renewal_requested", "Renewal Requested"), ("renew", "Renew"), ("do_not_renew", "Do Not Renew")], default="renewal_requested")
    decided_by = models.IntegerField(null=True, blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One decision per cycle (tracked by due_date)

    def __str__(self):
        return f"{self.APPLICATION} - {self.due_date} ({self.decision})"


class Appeal(TimeStampedModel):
    """Appeal record against a rejection."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="appeals")
    grounds = models.TextField()
    status = models.CharField(max_length=30, choices=[("submitted", "Submitted"), ("remanded_for_amendment", "Remanded for Amendment"), ("rejection_upheld", "Rejection Upheld"), ("decision_modified", "Decision Modified")], default="submitted")
    decided_by = models.IntegerField(null=True, blank=True)
    justification = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        unique_together = ["APPLICATION"]  # One appeal per application at a time

    def __str__(self):
        return f"{self.APPLICATION} - {self.status}"


class ApplicationHistory(TimeStampedModel):
    """Append-only history of application status changes and actions."""
    
    APPLICATION = models.ForeignKey(PatentApplication, on_delete=models.CASCADE, related_name="history")
    actor_id = models.IntegerField(db_index=True)  # User ID who performed the action
    action = models.CharField(max_length=50)  # e.g., "review", "assign", "withdraw"
    from_status = models.CharField(max_length=30, null=True, blank=True)
    to_status = models.CharField(max_length=30)
    note = models.TextField(blank=True)

    class Meta:
        app_label = "patent"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.APPLICATION} - {self.actor_id}: {self.action}"
