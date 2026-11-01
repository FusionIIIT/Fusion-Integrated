"""RSPC Database Models.
Follows ADR-0013: No cross-module foreign keys (users are plain integer user_ids).
Invariants enforced through database CheckConstraints and explicit named indexes.
"""

from decimal import Decimal

from django.db import models
from django.db.models import Q

from core.db.mixins import TimeStampedModel
from modules.rspc.domain.entities import (
    ClosureStatus,
    ConsultancyStatus,
    FinancialRequestStatus,
    ProcurementStatus,
    ProjectLifecycleStatus,
    ProposalStatus,
    StaffAppointmentStatus,
)


class ResearchProposal(TimeStampedModel):
    """Funded research project proposal submitted by faculty (PS 3.1, CW-RSPC-01)."""

    faculty_user_id = models.IntegerField(db_index=True)  # IAM user id
    department_id = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    objectives = models.TextField()
    funding_agency = models.CharField(max_length=255)
    duration_months = models.PositiveIntegerField(default=12)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    resource_requirements = models.TextField(blank=True, default="")
    policy_validation_passed = models.BooleanField(default=True)
    is_strategic = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in ProposalStatus],
        default=ProposalStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ProposalStatus]),
                name="rspc_proposal_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(budget_amount__gte=Decimal("0.00")),
                name="rspc_proposal_budget_non_negative",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="rspc_prop_status_idx"),
            models.Index(fields=["faculty_user_id", "-created_at"], name="rspc_prop_fac_idx"),
            models.Index(fields=["department_id", "status"], name="rspc_prop_dept_idx"),
        ]

    def __str__(self) -> str:
        return f"Proposal #{self.id}: {self.title} ({self.status})"


class ConsultancyProject(TimeStampedModel):
    """Consultancy project registered by faculty (PS 3.2, CW-RSPC-02)."""

    faculty_user_id = models.IntegerField(db_index=True)  # IAM user id
    department_id = models.CharField(max_length=64, db_index=True)
    title = models.CharField(max_length=255)
    client_name = models.CharField(max_length=255)
    client_details = models.TextField(blank=True, default="")
    scope = models.TextField()
    deliverables = models.TextField()
    duration_months = models.PositiveIntegerField(default=6)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    financial_terms = models.TextField(blank=True, default="")
    budget_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    requires_hod_review = models.BooleanField(default=True)
    is_strategic = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in ConsultancyStatus],
        default=ConsultancyStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ConsultancyStatus]),
                name="rspc_consultancy_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(budget_amount__gte=Decimal("0.00")),
                name="rspc_consult_budget_non_neg",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="rspc_cons_status_idx"),
            models.Index(fields=["faculty_user_id", "-created_at"], name="rspc_cons_fac_idx"),
        ]

    def __str__(self) -> str:
        return f"Consultancy #{self.id}: {self.title} ({self.client_name})"


class RSPCProject(TimeStampedModel):
    """Ongoing, completed, or archived institutional RSPC project (PS 1, UC-001, UC-021)."""

    project_code = models.CharField(max_length=64, unique=True, db_index=True)
    title = models.CharField(max_length=255)
    project_type = models.CharField(max_length=32)  # research / consultancy
    pi_user_id = models.IntegerField(db_index=True)  # Principal Investigator
    department_id = models.CharField(max_length=64, db_index=True)
    funding_source = models.CharField(max_length=255)
    sanctioned_budget = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    utilized_budget = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in ProjectLifecycleStatus],
        default=ProjectLifecycleStatus.ACTIVE.value,
        db_index=True,
    )
    milestones = models.JSONField(default=list, blank=True)
    progress_info = models.TextField(blank=True, default="")
    proposal = models.ForeignKey(
        ResearchProposal,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_projects",
    )
    consultancy = models.ForeignKey(
        ConsultancyProject,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="active_projects",
    )
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ProjectLifecycleStatus]),
                name="rspc_project_lifecycle_valid",
            ),
            models.CheckConstraint(
                condition=Q(sanctioned_budget__gte=Decimal("0.00")),
                name="rspc_proj_sanctioned_non_neg",
            ),
        ]
        indexes = [
            models.Index(fields=["pi_user_id", "status"], name="rspc_proj_pi_status_idx"),
            models.Index(fields=["department_id", "status"], name="rspc_proj_dept_status_idx"),
        ]

    def __str__(self) -> str:
        return f"Project [{self.project_code}]: {self.title} ({self.status})"

    @property
    def available_budget(self) -> Decimal:
        return max(Decimal("0.00"), self.sanctioned_budget - self.utilized_budget)


class ConsultancyMilestoneSettlement(TimeStampedModel):
    """Consultancy payments, deliverables, and settlements tracking (PS 3.2, UC-008)."""

    consultancy = models.ForeignKey(
        ConsultancyProject, on_delete=models.CASCADE, related_name="settlements"
    )
    milestone_name = models.CharField(max_length=160)
    deliverable_description = models.TextField(blank=True, default="")
    amount_due = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    amount_received = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    settlement_status = models.CharField(
        max_length=32, default="pending"
    )  # pending / partial / settled
    deliverable_status = models.CharField(
        max_length=32, default="pending"
    )  # pending / submitted / accepted

    class Meta:
        indexes = [
            models.Index(fields=["consultancy", "settlement_status"], name="rspc_cons_settle_idx"),
        ]


class StaffAppointmentRequest(TimeStampedModel):
    """Project-based staff appointment request & operational records (PS 3.3, CW-RSPC-03)."""

    project = models.ForeignKey(
        RSPCProject, on_delete=models.CASCADE, related_name="staff_appointments"
    )
    faculty_user_id = models.IntegerField(db_index=True)
    position_title = models.CharField(max_length=160)
    stipend_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    duration_months = models.PositiveIntegerField(default=6)
    advertisement_details = models.TextField(blank=True, default="")
    application_records = models.JSONField(default=list, blank=True)
    selection_committee_records = models.JSONField(default=list, blank=True)
    recommendation = models.TextField(blank=True, default="")
    recommended_candidate_name = models.CharField(max_length=255, blank=True, default="")
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in StaffAppointmentStatus],
        default=StaffAppointmentStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in StaffAppointmentStatus]),
                name="rspc_staff_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="rspc_staff_proj_status_idx"),
            models.Index(fields=["faculty_user_id", "status"], name="rspc_staff_fac_status_idx"),
        ]

    def __str__(self) -> str:
        return f"StaffRequest #{self.id}: {self.position_title} ({self.status})"


class FinancialRequest(TimeStampedModel):
    """Fund-utilization or expenditure request (PS 3.4, CW-RSPC-04)."""

    project = models.ForeignKey(
        RSPCProject, on_delete=models.CASCADE, related_name="financial_requests"
    )
    faculty_user_id = models.IntegerField(db_index=True)
    request_type = models.CharField(max_length=32)  # fund_utilization / expenditure
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    budget_head = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in FinancialRequestStatus],
        default=FinancialRequestStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in FinancialRequestStatus]),
                name="rspc_finance_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(amount__gt=Decimal("0.00")),
                name="rspc_finance_amount_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="rspc_fin_proj_status_idx"),
            models.Index(fields=["faculty_user_id", "-created_at"], name="rspc_fin_fac_idx"),
        ]

    def __str__(self) -> str:
        return f"FinanceRequest #{self.id} [{self.request_type}]: ₹{self.amount} ({self.status})"


class ProcurementRequest(TimeStampedModel):
    """Project equipment or consumable procurement request (PS 3.5, CW-RSPC-05)."""

    project = models.ForeignKey(
        RSPCProject, on_delete=models.CASCADE, related_name="procurement_requests"
    )
    faculty_user_id = models.IntegerField(db_index=True)
    item_type = models.CharField(max_length=32)  # equipment / consumable
    item_name = models.CharField(max_length=255)
    quantity = models.PositiveIntegerField(default=1)
    estimated_cost = models.DecimalField(max_digits=14, decimal_places=2)
    specifications = models.TextField(blank=True, default="")
    budget_validation_passed = models.BooleanField(default=True)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in ProcurementStatus],
        default=ProcurementStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ProcurementStatus]),
                name="rspc_proc_status_valid",
            ),
            models.CheckConstraint(
                condition=Q(estimated_cost__gt=Decimal("0.00")),
                name="rspc_proc_cost_positive",
            ),
        ]
        indexes = [
            models.Index(fields=["project", "status"], name="rspc_proc_proj_status_idx"),
            models.Index(fields=["faculty_user_id", "-created_at"], name="rspc_proc_fac_idx"),
        ]

    def __str__(self) -> str:
        return f"Procurement #{self.id}: {self.item_name} ({self.status})"


class ProgressReport(TimeStampedModel):
    """Periodic progress, utilization, and completion reports (PS 3.6, UC-014)."""

    project = models.ForeignKey(
        RSPCProject, on_delete=models.CASCADE, related_name="progress_reports"
    )
    faculty_user_id = models.IntegerField(db_index=True)
    report_type = models.CharField(max_length=32)  # progress / utilization / completion
    period_start = models.DateField()
    period_end = models.DateField()
    summary = models.TextField()
    expenditure_reported = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    status = models.CharField(max_length=32, default="submitted")

    class Meta:
        indexes = [
            models.Index(fields=["project", "-created_at"], name="rspc_rep_proj_idx"),
            models.Index(fields=["faculty_user_id", "-created_at"], name="rspc_rep_fac_idx"),
        ]

    def __str__(self) -> str:
        return f"Report #{self.id} [{self.report_type}] for {self.project.project_code}"


class ProjectClosureRecord(TimeStampedModel):
    """Project closure and completion verification record (PS 3.7, CW-RSPC-06)."""

    project = models.OneToOneField(
        RSPCProject, on_delete=models.CASCADE, related_name="closure_record"
    )
    faculty_user_id = models.IntegerField(db_index=True)
    completion_report = models.TextField()
    financial_settlement_record = models.TextField(blank=True, default="")
    asset_declaration_record = models.TextField(blank=True, default="")
    settlement_verified = models.BooleanField(default=False)
    assets_verified = models.BooleanField(default=False)
    status = models.CharField(
        max_length=32,
        choices=[(s.value, s.name) for s in ClosureStatus],
        default=ClosureStatus.DRAFT.value,
        db_index=True,
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=[s.value for s in ClosureStatus]),
                name="rspc_closure_status_valid",
            ),
        ]
        indexes = [
            models.Index(fields=["status", "-created_at"], name="rspc_closure_status_idx"),
        ]

    def __str__(self) -> str:
        return f"ClosureRecord for {self.project.project_code} ({self.status})"


class RSPCAuditTrail(models.Model):
    """Append-only audit trail and compliance log for RSPC events (PS 3.9)."""

    record_type = models.CharField(
        max_length=64, db_index=True
    )  # proposal, consultancy, staff, finance, etc.
    record_id = models.PositiveIntegerField(db_index=True)
    action = models.CharField(max_length=64)
    from_status = models.CharField(max_length=32, blank=True, default="")
    to_status = models.CharField(max_length=32, blank=True, default="")
    actor_user_id = models.IntegerField(null=True, blank=True, db_index=True)
    actor_role = models.CharField(max_length=64, blank=True, default="")
    remarks = models.TextField(blank=True, default="")
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["record_type", "record_id", "-timestamp"], name="rspc_audit_rec_idx"
            ),
            models.Index(fields=["actor_user_id", "-timestamp"], name="rspc_audit_actor_idx"),
        ]

    def __str__(self) -> str:
        return f"Audit [{self.record_type} #{self.record_id}]: {self.action}"


class RSPCNotification(TimeStampedModel):
    """In-app dashboard notification events for RSPC users (PS 3.8, UC-016, UC-031, BR-RSPC-061)."""

    recipient_user_id = models.IntegerField(db_index=True)
    category = models.CharField(
        max_length=64
    )  # proposal, pending_action, approval, rejection, deadline, finance
    title = models.CharField(max_length=255)
    message = models.TextField()
    record_type = models.CharField(max_length=64, blank=True, default="")
    record_id = models.PositiveIntegerField(null=True, blank=True)
    is_read = models.BooleanField(default=False, db_index=True)
    email_dispatched = models.BooleanField(default=False)

    class Meta:
        indexes = [
            models.Index(
                fields=["recipient_user_id", "is_read", "-created_at"], name="rspc_notif_user_idx"
            ),
        ]

    def __str__(self) -> str:
        return f"Notification to {self.recipient_user_id}: {self.title}"


class ExternalAgencyTracking(TimeStampedModel):
    """External agency submission/disbursement tracking (PS 3.9, UC-030)."""

    project = models.ForeignKey(
        RSPCProject,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="agency_trackings",
    )
    proposal_id = models.IntegerField(null=True, blank=True, db_index=True)
    agency_name = models.CharField(max_length=255)
    external_reference_number = models.CharField(max_length=128, db_index=True)
    submission_status = models.CharField(max_length=64, default="submitted")
    disbursement_status = models.CharField(max_length=64, default="pending")
    disbursement_amount = models.DecimalField(
        max_digits=14, decimal_places=2, default=Decimal("0.00")
    )
    updated_by_actor = models.CharField(max_length=64, blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["external_reference_number"], name="rspc_agency_ref_idx"),
        ]


class RSPCRoleSynchronizationLog(models.Model):
    """Audit log of RSPC role assignment synchronization events (PS 4, UC-018, BR-RSPC-055)."""

    user_id = models.IntegerField(db_index=True)
    previous_role = models.CharField(max_length=64, blank=True, default="")
    new_role = models.CharField(max_length=64)
    source_mechanism = models.CharField(max_length=128)
    synchronized_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"RoleSync user {self.user_id}: {self.previous_role} -> {self.new_role}"
