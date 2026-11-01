"""RSPC data models.

All person references are plain integer user_ids (IAM erp_user_id), never FKs
across module boundaries (ADR-0013).

Tables:
  rspc_project        — research project proposals
  rspc_project_transition
  rspc_consultancy    — consultancy project records
  rspc_consultancy_transition
  rspc_appointment    — project-based staff appointment requests
  rspc_appointment_transition
  rspc_finance        — fund utilisation / expenditure requests
  rspc_finance_transition
  rspc_procurement    — equipment / consumable procurement requests
  rspc_procurement_transition
  rspc_progress_report
  rspc_progress_report_transition
  rspc_closure        — project closure records
  rspc_closure_transition
"""

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel, UserScopedModel

from modules.rspc.domain.state_machine import (
    ProposalStatus, ConsultancyStatus, AppointmentStatus,
    FinanceStatus, ProcurementStatus, ProgressReportStatus, ClosureStatus,
)


# ---------------------------------------------------------------------------
# Research Project Proposal
# ---------------------------------------------------------------------------

class ResearchProject(TimeStampedModel, UserScopedModel):
    """A research project proposal submitted by a Faculty member."""

    STATUS_CHOICES = [
        (ProposalStatus.DRAFT,              "Draft"),
        (ProposalStatus.SUBMITTED,          "Submitted"),
        (ProposalStatus.HOD_REVIEW,         "HoD Review"),
        (ProposalStatus.HOD_RECOMMENDED,    "HoD Recommended"),
        (ProposalStatus.HOD_NOT_RECOMMENDED,"HoD Not Recommended"),
        (ProposalStatus.ADMIN_VERIFIED,     "Admin Verified"),
        (ProposalStatus.DEAN_APPROVED,      "Dean Approved"),
        (ProposalStatus.DEAN_REJECTED,      "Dean Rejected"),
        (ProposalStatus.FORWARDED_DIRECTOR, "Forwarded to Director"),
        (ProposalStatus.DIRECTOR_APPROVED,  "Director Approved"),
        (ProposalStatus.DIRECTOR_REJECTED,  "Director Rejected"),
    ]

    # Core proposal fields
    title            = models.CharField(max_length=300)
    objectives       = models.TextField(blank=True)
    funding_source   = models.CharField(max_length=200, blank=True)
    budget_requested = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True,
        help_text="Total budget requested in INR")
    start_date       = models.DateField(null=True, blank=True)
    end_date         = models.DateField(null=True, blank=True)
    resource_requirements = models.TextField(blank=True)
    department       = models.CharField(max_length=100, blank=True)
    status           = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=ProposalStatus.DRAFT)

    # Review metadata (set by each reviewer stage)
    hod_user_id      = models.IntegerField(null=True, blank=True, db_index=True)
    hod_remarks      = models.CharField(max_length=1000, blank=True)
    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)
    director_remarks = models.CharField(max_length=1000, blank=True)

    # Timestamps for each decision
    submitted_at        = models.DateTimeField(null=True, blank=True)
    hod_decided_at      = models.DateTimeField(null=True, blank=True)
    admin_verified_at   = models.DateTimeField(null=True, blank=True)
    dean_decided_at     = models.DateTimeField(null=True, blank=True)
    director_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_project"
        indexes = [
            models.Index(fields=["status", "-created_at"], name="rspc_project_status_idx"),
            models.Index(fields=["user_id", "-created_at"],  name="rspc_project_user_idx"),
            models.Index(fields=["hod_user_id"],              name="rspc_project_hod_idx"),
        ]
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s for s, _ in [
                    (ProposalStatus.DRAFT, ""),
                    (ProposalStatus.SUBMITTED, ""),
                    (ProposalStatus.HOD_REVIEW, ""),
                    (ProposalStatus.HOD_RECOMMENDED, ""),
                    (ProposalStatus.HOD_NOT_RECOMMENDED, ""),
                    (ProposalStatus.ADMIN_VERIFIED, ""),
                    (ProposalStatus.DEAN_APPROVED, ""),
                    (ProposalStatus.DEAN_REJECTED, ""),
                    (ProposalStatus.FORWARDED_DIRECTOR, ""),
                    (ProposalStatus.DIRECTOR_APPROVED, ""),
                    (ProposalStatus.DIRECTOR_REJECTED, ""),
                ]]),
                name="rspc_project_status_valid",
            )
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.title} (user {self.user_id})"


class ResearchProjectTransition(models.Model):
    """Append-only audit trail for every status change on a research project."""
    project      = models.ForeignKey(
        ResearchProject, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=30)
    to_status    = models.CharField(max_length=30)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_project_transition"
        indexes  = [models.Index(fields=["project", "at"],
                                 name="rspc_proj_trans_idx")]

    def __str__(self) -> str:
        return (f"proj#{self.project_id} "
                f"{self.from_status}->{self.to_status}")


# ---------------------------------------------------------------------------
# Consultancy Project
# ---------------------------------------------------------------------------

class ConsultancyProject(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (ConsultancyStatus.DRAFT,              "Draft"),
        (ConsultancyStatus.SUBMITTED,          "Submitted"),
        (ConsultancyStatus.HOD_REVIEW,         "HoD Review"),
        (ConsultancyStatus.HOD_RECOMMENDED,    "HoD Recommended"),
        (ConsultancyStatus.ADMIN_VERIFIED,     "Admin Verified"),
        (ConsultancyStatus.DEAN_APPROVED,      "Dean Approved"),
        (ConsultancyStatus.DEAN_REJECTED,      "Dean Rejected"),
        (ConsultancyStatus.FORWARDED_DIRECTOR, "Forwarded to Director"),
        (ConsultancyStatus.DIRECTOR_APPROVED,  "Director Approved"),
        (ConsultancyStatus.DIRECTOR_REJECTED,  "Director Rejected"),
    ]

    title          = models.CharField(max_length=300)
    client_name    = models.CharField(max_length=200, blank=True)
    client_details = models.TextField(blank=True)
    scope          = models.TextField(blank=True)
    deliverables   = models.TextField(blank=True)
    financial_terms = models.TextField(blank=True)
    total_amount   = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    start_date     = models.DateField(null=True, blank=True)
    end_date       = models.DateField(null=True, blank=True)
    department     = models.CharField(max_length=100, blank=True)
    status         = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=ConsultancyStatus.DRAFT)

    hod_user_id      = models.IntegerField(null=True, blank=True, db_index=True)
    hod_remarks      = models.CharField(max_length=1000, blank=True)
    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)
    director_remarks = models.CharField(max_length=1000, blank=True)

    submitted_at        = models.DateTimeField(null=True, blank=True)
    hod_decided_at      = models.DateTimeField(null=True, blank=True)
    admin_verified_at   = models.DateTimeField(null=True, blank=True)
    dean_decided_at     = models.DateTimeField(null=True, blank=True)
    director_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_consultancy"
        indexes  = [
            models.Index(fields=["status", "-created_at"], name="rspc_cons_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="rspc_cons_user_idx"),
        ]

    def __str__(self) -> str:
        return f"[{self.status}] {self.title}"


class ConsultancyTransition(models.Model):
    consultancy  = models.ForeignKey(
        ConsultancyProject, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=30)
    to_status    = models.CharField(max_length=30)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_consultancy_transition"
        indexes  = [models.Index(fields=["consultancy", "at"],
                                 name="rspc_cons_trans_idx")]


# ---------------------------------------------------------------------------
# Staff Appointment
# ---------------------------------------------------------------------------

class StaffAppointment(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (AppointmentStatus.DRAFT,                    "Draft"),
        (AppointmentStatus.REQUESTED,                "Requested"),
        (AppointmentStatus.ADMIN_VERIFIED,           "Admin Verified"),
        (AppointmentStatus.SELECTION_RECOMMENDATION, "Selection Recommendation Recorded"),
        (AppointmentStatus.APPROVED,                 "Approved"),
        (AppointmentStatus.FORWARDED_DIRECTOR,       "Forwarded to Director"),
        (AppointmentStatus.DIRECTOR_APPROVED,        "Director Approved"),
        (AppointmentStatus.REJECTED,                 "Rejected"),
    ]

    project      = models.ForeignKey(
        ResearchProject, on_delete=models.PROTECT,
        related_name="appointments", null=True, blank=True)
    position_title = models.CharField(max_length=200)
    stipend_amount = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True)
    duration_months = models.PositiveSmallIntegerField(null=True, blank=True)
    department     = models.CharField(max_length=100, blank=True)
    status         = models.CharField(
        max_length=40, choices=STATUS_CHOICES, default=AppointmentStatus.DRAFT)

    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)
    director_remarks = models.CharField(max_length=1000, blank=True)
    selection_remarks = models.CharField(max_length=1000, blank=True)

    submitted_at        = models.DateTimeField(null=True, blank=True)
    admin_verified_at   = models.DateTimeField(null=True, blank=True)
    dean_decided_at     = models.DateTimeField(null=True, blank=True)
    director_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_appointment"
        indexes  = [
            models.Index(fields=["status", "-created_at"], name="rspc_appt_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="rspc_appt_user_idx"),
        ]


class AppointmentTransition(models.Model):
    appointment  = models.ForeignKey(
        StaffAppointment, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=40)
    to_status    = models.CharField(max_length=40)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_appointment_transition"
        indexes  = [models.Index(fields=["appointment", "at"],
                                 name="rspc_appt_trans_idx")]


# ---------------------------------------------------------------------------
# Financial / Fund Request
# ---------------------------------------------------------------------------

class FinanceRequest(TimeStampedModel, UserScopedModel):
    CATEGORY_CHOICES = [
        ("fund_utilisation", "Fund Utilisation"),
        ("expenditure",      "Expenditure"),
        ("advance",          "Advance"),
    ]
    STATUS_CHOICES = [
        (FinanceStatus.DRAFT,              "Draft"),
        (FinanceStatus.SUBMITTED,          "Submitted"),
        (FinanceStatus.VERIFIED,           "Verified"),
        (FinanceStatus.APPROVED,           "Approved"),
        (FinanceStatus.FORWARDED_DIRECTOR, "Forwarded to Director"),
        (FinanceStatus.DIRECTOR_APPROVED,  "Director Approved"),
        (FinanceStatus.REJECTED,           "Rejected"),
    ]

    project       = models.ForeignKey(
        ResearchProject, on_delete=models.PROTECT,
        related_name="finance_requests", null=True, blank=True)
    category      = models.CharField(
        max_length=30, choices=CATEGORY_CHOICES, default="expenditure")
    description   = models.TextField()
    amount        = models.DecimalField(max_digits=14, decimal_places=2)
    purpose       = models.CharField(max_length=500, blank=True)
    status        = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=FinanceStatus.DRAFT)

    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)
    director_remarks = models.CharField(max_length=1000, blank=True)

    submitted_at        = models.DateTimeField(null=True, blank=True)
    admin_verified_at   = models.DateTimeField(null=True, blank=True)
    dean_decided_at     = models.DateTimeField(null=True, blank=True)
    director_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_finance"
        indexes  = [
            models.Index(fields=["status", "-created_at"], name="rspc_fin_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="rspc_fin_user_idx"),
        ]


class FinanceTransition(models.Model):
    request      = models.ForeignKey(
        FinanceRequest, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=30)
    to_status    = models.CharField(max_length=30)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_finance_transition"
        indexes  = [models.Index(fields=["request", "at"],
                                 name="rspc_fin_trans_idx")]


# ---------------------------------------------------------------------------
# Procurement Request
# ---------------------------------------------------------------------------

class ProcurementRequest(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (ProcurementStatus.DRAFT,              "Draft"),
        (ProcurementStatus.SUBMITTED,          "Submitted"),
        (ProcurementStatus.VERIFIED,           "Verified"),
        (ProcurementStatus.APPROVED,           "Approved"),
        (ProcurementStatus.FORWARDED_DIRECTOR, "Forwarded to Director"),
        (ProcurementStatus.DIRECTOR_APPROVED,  "Director Approved"),
        (ProcurementStatus.REJECTED,           "Rejected"),
    ]

    project        = models.ForeignKey(
        ResearchProject, on_delete=models.PROTECT,
        related_name="procurement_requests", null=True, blank=True)
    item_description = models.TextField()
    quantity       = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2)
    justification  = models.TextField(blank=True)
    status         = models.CharField(
        max_length=30, choices=STATUS_CHOICES, default=ProcurementStatus.DRAFT)

    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)
    director_remarks = models.CharField(max_length=1000, blank=True)

    submitted_at        = models.DateTimeField(null=True, blank=True)
    admin_verified_at   = models.DateTimeField(null=True, blank=True)
    dean_decided_at     = models.DateTimeField(null=True, blank=True)
    director_decided_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_procurement"
        indexes  = [
            models.Index(fields=["status", "-created_at"], name="rspc_proc_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="rspc_proc_user_idx"),
        ]


class ProcurementTransition(models.Model):
    request      = models.ForeignKey(
        ProcurementRequest, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=30)
    to_status    = models.CharField(max_length=30)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_procurement_transition"
        indexes  = [models.Index(fields=["request", "at"],
                                 name="rspc_proc_trans_idx")]


# ---------------------------------------------------------------------------
# Progress Report
# ---------------------------------------------------------------------------

class ProgressReport(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (ProgressReportStatus.DRAFT,     "Draft"),
        (ProgressReportStatus.SUBMITTED, "Submitted"),
        (ProgressReportStatus.ACCEPTED,  "Accepted"),
        (ProgressReportStatus.RETURNED,  "Returned for Revision"),
    ]

    project       = models.ForeignKey(
        ResearchProject, on_delete=models.PROTECT,
        related_name="progress_reports")
    reporting_period = models.CharField(max_length=100,
                                        help_text="e.g. Q1 2026-27")
    summary       = models.TextField()
    milestones_achieved = models.TextField(blank=True)
    expenditure_so_far  = models.DecimalField(
        max_digits=14, decimal_places=2, null=True, blank=True)
    status        = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=ProgressReportStatus.DRAFT)

    reviewer_remarks = models.CharField(max_length=1000, blank=True)
    submitted_at     = models.DateTimeField(null=True, blank=True)
    reviewed_at      = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_progress_report"
        indexes  = [
            models.Index(fields=["project", "status"], name="rspc_pr_proj_idx"),
            models.Index(fields=["user_id", "-created_at"],  name="rspc_pr_user_idx"),
        ]


class ProgressReportTransition(models.Model):
    report       = models.ForeignKey(
        ProgressReport, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=20)
    to_status    = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_progress_report_transition"
        indexes  = [models.Index(fields=["report", "at"],
                                 name="rspc_pr_trans_idx")]


# ---------------------------------------------------------------------------
# Project Closure
# ---------------------------------------------------------------------------

class ProjectClosure(TimeStampedModel, UserScopedModel):
    STATUS_CHOICES = [
        (ClosureStatus.DRAFT,          "Draft"),
        (ClosureStatus.SUBMITTED,      "Submitted"),
        (ClosureStatus.ADMIN_VERIFIED, "Admin Verified"),
        (ClosureStatus.DEAN_APPROVED,  "Dean Approved"),
        (ClosureStatus.DEAN_REJECTED,  "Dean Rejected"),
    ]

    project       = models.OneToOneField(
        ResearchProject, on_delete=models.PROTECT,
        related_name="closure")
    completion_summary = models.TextField()
    financial_settlement_details = models.TextField(blank=True)
    assets_declared  = models.TextField(blank=True)
    status           = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=ClosureStatus.DRAFT)

    admin_remarks    = models.CharField(max_length=1000, blank=True)
    dean_remarks     = models.CharField(max_length=1000, blank=True)

    submitted_at      = models.DateTimeField(null=True, blank=True)
    admin_verified_at = models.DateTimeField(null=True, blank=True)
    dean_decided_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "rspc_closure"
        indexes  = [
            models.Index(fields=["status", "-created_at"], name="rspc_clos_status_idx"),
            models.Index(fields=["user_id", "-created_at"], name="rspc_clos_user_idx"),
        ]


class ClosureTransition(models.Model):
    closure      = models.ForeignKey(
        ProjectClosure, on_delete=models.CASCADE, related_name="transitions")
    from_status  = models.CharField(max_length=20)
    to_status    = models.CharField(max_length=20)
    actor_user_id = models.IntegerField(null=True, blank=True)
    remarks      = models.CharField(max_length=1000, blank=True)
    at           = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_closure_transition"
        indexes  = [models.Index(fields=["closure", "at"],
                                 name="rspc_clos_trans_idx")]
