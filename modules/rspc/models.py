"""Database models for Research, Sponsored Projects & Consultancy (RSPC) module.

Follows Fusion ERP architectural constraints (ADR-0013):
- No cross-module ForeignKeys.
- References to users and actors use plain integer IDs (pi_id, requested_by_id, actor_id).
- Clean relational separation and domain integrity.
"""
from __future__ import annotations

from django.db import models


class ResearchProposal(models.Model):
    """Research Project Proposal (CFR-RSPC-006, CFR-RSPC-007, BR-RSPC-012)."""

    title = models.CharField(max_length=255, help_text="Title of the research project")
    pi_id = models.IntegerField(help_text="User ID of Principal Investigator (plain int)")
    department = models.CharField(max_length=100)
    funding_agency = models.CharField(max_length=200)
    scheme_name = models.CharField(max_length=200, blank=True, default="")
    budget = models.DecimalField(max_digits=14, decimal_places=2)
    objectives = models.TextField()
    timeline_months = models.PositiveIntegerField(default=12)
    start_date = models.DateField()
    end_date = models.DateField()
    resource_requirements = models.TextField(blank=True, default="")
    is_strategic = models.BooleanField(default=False)
    status = models.CharField(max_length=40, default="DRAFT", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_research_proposal"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} (PI: {self.pi_id}, Status: {self.status})"


class ConsultancyProject(models.Model):
    """Consultancy Project Registration (CFR-RSPC-009, CFR-RSPC-010, BR-RSPC-022)."""

    title = models.CharField(max_length=255)
    pi_id = models.IntegerField(help_text="User ID of Faculty Consultant (plain int)")
    client_name = models.CharField(max_length=200)
    client_address = models.TextField(blank=True, default="")
    scope_of_work = models.TextField()
    deliverables = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField()
    total_cost = models.DecimalField(max_digits=14, decimal_places=2)
    institutional_share = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="DRAFT", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_consultancy_project"
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Consultancy: {self.title} (Client: {self.client_name})"


class ProjectStaffAppointment(models.Model):
    """Project-based Staff Appointment Operational Record (CFR-RSPC-012, BR-RSPC-026)."""

    project_id = models.IntegerField(help_text="Project ID (ResearchProposal or Consultancy)")
    project_type = models.CharField(max_length=20, default="research")
    pi_id = models.IntegerField(help_text="User ID of PI")
    position_title = models.CharField(max_length=100)
    stipend_amount = models.DecimalField(max_digits=12, decimal_places=2)
    duration_months = models.PositiveIntegerField(default=6)
    advertisement_details = models.TextField(blank=True, default="")
    selected_candidate_name = models.CharField(max_length=150, blank=True, default="")
    status = models.CharField(max_length=40, default="REQUESTED", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_staff_appointment"
        ordering = ["-created_at"]


class FinancialRequest(models.Model):
    """Fund Utilization and Expenditure Request (CFR-RSPC-015, CFR-RSPC-016, BR-RSPC-032)."""

    project_id = models.IntegerField()
    project_type = models.CharField(max_length=20, default="research")
    requested_by_id = models.IntegerField(help_text="User ID of requester")
    budget_head = models.CharField(max_length=100)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    purpose = models.TextField()
    status = models.CharField(max_length=40, default="SUBMITTED", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_financial_request"
        ordering = ["-created_at"]


class ProcurementRequest(models.Model):
    """Equipment and Consumables Procurement Request (CFR-RSPC-017, BR-RSPC-035)."""

    project_id = models.IntegerField()
    project_type = models.CharField(max_length=20, default="research")
    requested_by_id = models.IntegerField()
    item_name = models.CharField(max_length=200)
    item_type = models.CharField(max_length=50, default="equipment")
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2)
    specifications = models.TextField(blank=True, default="")
    status = models.CharField(max_length=40, default="REQUESTED", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_procurement_request"
        ordering = ["-created_at"]


class ProgressReport(models.Model):
    """Periodic Progress and Utilization Reporting (CFR-RSPC-018, BR-RSPC-037)."""

    project_id = models.IntegerField()
    project_type = models.CharField(max_length=20, default="research")
    submitted_by_id = models.IntegerField()
    report_type = models.CharField(max_length=50, default="periodic")
    period_start = models.DateField()
    period_end = models.DateField()
    summary = models.TextField()
    achievements = models.TextField(blank=True, default="")
    funds_utilized = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    status = models.CharField(max_length=40, default="SUBMITTED")

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_progress_report"
        ordering = ["-created_at"]


class ProjectClosure(models.Model):
    """Project Closure and Completion Processing (CFR-RSPC-020, BR-RSPC-043)."""

    project_id = models.IntegerField()
    project_type = models.CharField(max_length=20, default="research")
    submitted_by_id = models.IntegerField()
    financial_settlement_status = models.CharField(max_length=50, default="settled")
    asset_declaration = models.TextField()
    closure_summary = models.TextField()
    status = models.CharField(max_length=40, default="REQUESTED", db_index=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "rspc_project_closure"
        ordering = ["-created_at"]


class RSPCAuditTrail(models.Model):
    """Structured Audit and Compliance Log (CFR-RSPC-002, CFR-RSPC-008, BR-RSPC-050)."""

    entity_type = models.CharField(max_length=50)
    entity_id = models.IntegerField()
    actor_id = models.IntegerField(help_text="User ID who executed the action")
    action = models.CharField(max_length=50)
    remarks = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "rspc_audit_trail"
        ordering = ["-timestamp"]


class RSPCNotification(models.Model):
    """RSPC Event Notification Record (CFR-RSPC-021, BR-RSPC-061)."""

    recipient_id = models.IntegerField(help_text="User ID of recipient", db_index=True)
    event_type = models.CharField(max_length=50)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "rspc_notification"
        ordering = ["-created_at"]
