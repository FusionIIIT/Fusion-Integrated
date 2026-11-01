from django.db import models

from core.db.mixins import TimeStampedModel
from modules.directory.models import UserRef


class ResearchProposal(TimeStampedModel):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("submitted", "Submitted"),
        ("hod_approved", "HoD Approved"),
        ("admin_verified", "Admin Verified"),
        ("dean_approved", "Dean Approved"),
        ("director_approved", "Director Approved"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(max_length=255)
    faculty = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name="research_proposals")
    department = models.CharField(max_length=100)
    funding_agency = models.CharField(max_length=200)
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    objectives = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_research_proposal"
        verbose_name_plural = "Research Proposals"

    def __str__(self) -> str:
        return f"{self.title} - {self.faculty.username} ({self.status})"


class ConsultancyProject(TimeStampedModel):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("hod_approved", "HoD Approved"),
        ("dean_approved", "Dean Approved"),
        ("rejected", "Rejected"),
    ]

    title = models.CharField(max_length=255)
    faculty = models.ForeignKey(UserRef, on_delete=models.CASCADE, related_name="consultancy_projects")
    client_name = models.CharField(max_length=200)
    financial_terms = models.DecimalField(max_digits=12, decimal_places=2)
    deliverables = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")

    class Meta:
        db_table = "rspc_consultancy_project"
        verbose_name_plural = "Consultancy Projects"

    def __str__(self) -> str:
        return f"{self.title} - {self.client_name}"


class ProjectStaffAppointment(TimeStampedModel):
    STATUS_CHOICES = [
        ("requested", "Requested"),
        ("admin_verified", "Admin Verified"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    ]

    proposal = models.ForeignKey(
        ResearchProposal, on_delete=models.CASCADE, related_name="staff_appointments"
    )
    position_title = models.CharField(max_length=100)
    candidate_name = models.CharField(max_length=150, blank=True)
    stipend = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="requested")

    class Meta:
        db_table = "rspc_staff_appointment"
        verbose_name_plural = "Project Staff Appointments"

    def __str__(self) -> str:
        return f"{self.position_title} - {self.proposal.title}"


class FundRequest(TimeStampedModel):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("admin_verified", "Admin Verified"),
        ("dean_approved", "Dean Approved"),
        ("director_approved", "Director Approved"),
        ("rejected", "Rejected"),
    ]

    proposal = models.ForeignKey(ResearchProposal, on_delete=models.CASCADE, related_name="fund_requests")
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="submitted")

    class Meta:
        db_table = "rspc_fund_request"
        verbose_name_plural = "Fund Requests"

    def __str__(self) -> str:
        return f"Fund Request: {self.proposal.title} - {self.requested_amount}"
