"""RSPC data layer: research proposals, consultancy, project staff and fund requests.

Faculty are referenced by IAM user id (a plain integer), never by a ForeignKey to
``directory.UserRef``: ``ops/checks/no_cross_module_fk.py`` forbids FKs that cross a
module boundary. Foreign keys *within* this module are fine.

Statuses mirror the approval chain (HoD -> Admin -> Dean -> Director). The transition
rules themselves are not implemented here; this layer only stores the state.
"""

from django.db import models

from core.db.mixins import TimeStampedModel


class ResearchProposal(TimeStampedModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        SUBMITTED = "submitted", "Submitted"
        HOD_APPROVED = "hod_approved", "HoD Approved"
        ADMIN_VERIFIED = "admin_verified", "Admin Verified"
        DEAN_APPROVED = "dean_approved", "Dean Approved"
        DIRECTOR_APPROVED = "director_approved", "Director Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=255)
    faculty_user_id = models.IntegerField(db_index=True)  # IAM user id — NO FK
    department = models.CharField(max_length=100)
    funding_agency = models.CharField(max_length=200)
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    objectives = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.DRAFT)
    remarks = models.TextField(blank=True)

    class Meta:
        db_table = "rspc_research_proposal"
        verbose_name_plural = "Research proposals"

    def __str__(self) -> str:
        return f"{self.title} ({self.status})"


class ConsultancyProject(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        HOD_APPROVED = "hod_approved", "HoD Approved"
        DEAN_APPROVED = "dean_approved", "Dean Approved"
        REJECTED = "rejected", "Rejected"

    title = models.CharField(max_length=255)
    faculty_user_id = models.IntegerField(db_index=True)  # IAM user id — NO FK
    client_name = models.CharField(max_length=200)
    financial_terms = models.DecimalField(max_digits=12, decimal_places=2)
    deliverables = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)

    class Meta:
        db_table = "rspc_consultancy_project"
        verbose_name_plural = "Consultancy projects"

    def __str__(self) -> str:
        return f"{self.title} - {self.client_name}"


class ProjectStaffAppointment(TimeStampedModel):
    class Status(models.TextChoices):
        REQUESTED = "requested", "Requested"
        ADMIN_VERIFIED = "admin_verified", "Admin Verified"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    proposal = models.ForeignKey(
        ResearchProposal, on_delete=models.CASCADE, related_name="staff_appointments"
    )
    position_title = models.CharField(max_length=100)
    candidate_name = models.CharField(max_length=150, blank=True)
    stipend = models.DecimalField(max_digits=10, decimal_places=2)
    duration_months = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.REQUESTED)

    class Meta:
        db_table = "rspc_staff_appointment"
        verbose_name_plural = "Project staff appointments"

    def __str__(self) -> str:
        return f"{self.position_title} - proposal {self.proposal_id}"


class FundRequest(TimeStampedModel):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        ADMIN_VERIFIED = "admin_verified", "Admin Verified"
        DEAN_APPROVED = "dean_approved", "Dean Approved"
        DIRECTOR_APPROVED = "director_approved", "Director Approved"
        REJECTED = "rejected", "Rejected"

    proposal = models.ForeignKey(
        ResearchProposal, on_delete=models.CASCADE, related_name="fund_requests"
    )
    requested_amount = models.DecimalField(max_digits=12, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.SUBMITTED)

    class Meta:
        db_table = "rspc_fund_request"
        verbose_name_plural = "Fund requests"

    def __str__(self) -> str:
        return f"Fund request {self.requested_amount} - proposal {self.proposal_id}"
