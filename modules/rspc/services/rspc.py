"""RSPC Domain Services.
Follows the Fusion ERP rule: All mutations go through services within a transaction.atomic block.
Services raise domain errors, never DRF errors.
Audit trails and notifications are created atomically with state updates.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from modules.rspc.domain.entities import (
    ClosureStatus,
    ConsultancyStatus,
    FinancialRequestStatus,
    ProcurementStatus,
    ProjectLifecycleStatus,
    ProposalStatus,
    RspcRole,
    StaffAppointmentStatus,
)
from modules.rspc.domain.errors import (
    BudgetExceededError,
    LifecycleNotPermittedError,
    MandatoryFieldMissingError,
)
from modules.rspc.domain.state_machine import (
    CLOSURE_TRANSITIONS,
    CONSULTANCY_TRANSITIONS,
    FINANCE_TRANSITIONS,
    PROCUREMENT_TRANSITIONS,
    PROPOSAL_TRANSITIONS,
    STAFF_TRANSITIONS,
    validate_transition,
)
from modules.rspc.models import (
    ConsultancyMilestoneSettlement,
    ConsultancyProject,
    ExternalAgencyTracking,
    FinancialRequest,
    ProcurementRequest,
    ProgressReport,
    ProjectClosureRecord,
    ResearchProposal,
    RSPCAuditTrail,
    RSPCNotification,
    RSPCProject,
    RSPCRoleSynchronizationLog,
    StaffAppointmentRequest,
)


def _determine_actor_role(principal) -> str:
    """Resolve normalized RSPC role string for the principal."""
    if principal is None:
        return RspcRole.SYSTEM.value
    # Check active_role or permissions
    active = getattr(principal, "active_role", None) or ""
    act_lower = str(active).lower().replace(" ", "_").replace("-", "_")
    if "director" in act_lower:
        return RspcRole.DIRECTOR.value
    if "dean" in act_lower:
        return RspcRole.DEAN_RSPC.value
    if "admin" in act_lower:
        return RspcRole.RSPC_ADMIN.value
    if "hod" in act_lower or "head" in act_lower:
        return RspcRole.HOD.value
    if "faculty" in act_lower:
        return RspcRole.FACULTY.value

    # Fallback to permission capabilities
    if principal.has_permission("rspc.proposal.authorize_director"):
        return RspcRole.DIRECTOR.value
    if principal.has_permission("rspc.proposal.approve_dean"):
        return RspcRole.DEAN_RSPC.value
    if principal.has_permission("rspc.proposal.verify"):
        return RspcRole.RSPC_ADMIN.value
    if principal.has_permission("rspc.proposal.recommend_dept"):
        return RspcRole.HOD.value
    return RspcRole.FACULTY.value


def log_audit(
    *,
    record_type: str,
    record_id: int,
    action: str,
    from_status: str = "",
    to_status: str = "",
    principal: Any = None,
    remarks: str = "",
) -> RSPCAuditTrail:
    """Record an immutable audit trail entry (BR-RSPC-015, BR-RSPC-016, BR-RSPC-050)."""
    user_id = getattr(principal, "user_id", None) if principal else None
    role = _determine_actor_role(principal)
    return RSPCAuditTrail.objects.create(
        record_type=record_type,
        record_id=record_id,
        action=action,
        from_status=from_status,
        to_status=to_status,
        actor_user_id=user_id,
        actor_role=role,
        remarks=remarks,
    )


def create_notification(
    *,
    recipient_user_id: int,
    category: str,
    title: str,
    message: str,
    record_type: str = "",
    record_id: int | None = None,
) -> RSPCNotification:
    """Dispatch an in-app notification event (PS 3.8, UC-031, BR-RSPC-061)."""
    return RSPCNotification.objects.create(
        recipient_user_id=recipient_user_id,
        category=category,
        title=title,
        message=message,
        record_type=record_type,
        record_id=record_id,
        is_read=False,
    )


# ---------------------------------------------------------------------------
# 1. Research Proposal Services (UC-002..006, CW-RSPC-01)
# ---------------------------------------------------------------------------
def submit_research_proposal(
    *,
    faculty_user_id: int,
    department_id: str,
    title: str,
    objectives: str,
    funding_agency: str,
    duration_months: int,
    budget_amount: Decimal | float | str,
    resource_requirements: str = "",
    is_strategic: bool = False,
    start_date: Any = None,
    end_date: Any = None,
    principal: Any = None,
) -> ResearchProposal:
    """Faculty submits a new research proposal (UC-002, BR-RSPC-013, BR-RSPC-014)."""
    budget_dec = Decimal(str(budget_amount))

    # Mandatory field check (BR-RSPC-013)
    missing = []
    if not title:
        missing.append("title")
    if not objectives:
        missing.append("objectives")
    if not funding_agency:
        missing.append("funding_agency")
    if not budget_dec or budget_dec <= Decimal("0.00"):
        missing.append("budget_amount")
    if missing:
        raise MandatoryFieldMissingError(missing)

    with transaction.atomic():
        proposal = ResearchProposal.objects.create(
            faculty_user_id=faculty_user_id,
            department_id=department_id,
            title=title,
            objectives=objectives,
            funding_agency=funding_agency,
            duration_months=duration_months,
            budget_amount=budget_dec,
            resource_requirements=resource_requirements,
            is_strategic=is_strategic,
            start_date=start_date,
            end_date=end_date,
            status=ProposalStatus.SUBMITTED.value,
        )

        log_audit(
            record_type="proposal",
            record_id=proposal.id,
            action="submit_proposal",
            from_status=ProposalStatus.DRAFT.value,
            to_status=ProposalStatus.SUBMITTED.value,
            principal=principal,
            remarks="Proposal submitted by faculty",
        )

        create_notification(
            recipient_user_id=faculty_user_id,
            category="proposal",
            title="Research Proposal Submitted",
            message=f"Your proposal '{title}' has been submitted and routed for HoD review.",
            record_type="proposal",
            record_id=proposal.id,
        )

    return proposal


def transition_proposal(
    *,
    proposal_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
) -> ResearchProposal:
    """Transition proposal state along CW-RSPC-01."""
    with transaction.atomic():
        proposal = ResearchProposal.objects.select_for_update().get(pk=proposal_id)
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "budget_amount": proposal.budget_amount,
            "is_strategic": proposal.is_strategic,
            "is_eligible": is_eligible,
            "policy_validation_passed": proposal.policy_validation_passed,
        }

        validate_transition(
            transitions=PROPOSAL_TRANSITIONS,
            from_state=proposal.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"Proposal #{proposal.id}",
        )

        frm = proposal.status
        proposal.status = to_status
        proposal.save(update_fields=["status", "updated_at"])

        log_audit(
            record_type="proposal",
            record_id=proposal.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        # Notify PI
        create_notification(
            recipient_user_id=proposal.faculty_user_id,
            category="proposal",
            title=f"Proposal Status Updated: {to_status}",
            message=f"Proposal #{proposal.id} moved to {to_status}. Remarks: {remarks}",
            record_type="proposal",
            record_id=proposal.id,
        )

        # If approved, instantiate or activate the RSPCProject
        if to_status == ProposalStatus.APPROVED.value:
            code = f"RP-{proposal.id:04d}"
            RSPCProject.objects.get_or_create(
                project_code=code,
                defaults={
                    "title": proposal.title,
                    "project_type": "research",
                    "pi_user_id": proposal.faculty_user_id,
                    "department_id": proposal.department_id,
                    "funding_source": proposal.funding_agency,
                    "sanctioned_budget": proposal.budget_amount,
                    "utilized_budget": Decimal("0.00"),
                    "status": ProjectLifecycleStatus.ACTIVE.value,
                    "proposal": proposal,
                },
            )

    return proposal


# ---------------------------------------------------------------------------
# 2. Consultancy Project Services (UC-007, 008, CW-RSPC-02)
# ---------------------------------------------------------------------------
def register_consultancy(
    *,
    faculty_user_id: int,
    department_id: str,
    title: str,
    client_name: str,
    scope: str,
    deliverables: str,
    duration_months: int,
    budget_amount: Decimal | float | str,
    client_details: str = "",
    financial_terms: str = "",
    requires_hod_review: bool = True,
    is_strategic: bool = False,
    start_date: Any = None,
    end_date: Any = None,
    principal: Any = None,
) -> ConsultancyProject:
    """Faculty registers a consultancy project (UC-007, BR-RSPC-022)."""
    budget_dec = Decimal(str(budget_amount))
    missing = []
    if not title:
        missing.append("title")
    if not client_name:
        missing.append("client_name")
    if not scope:
        missing.append("scope")
    if not deliverables:
        missing.append("deliverables")
    if missing:
        raise MandatoryFieldMissingError(missing)

    with transaction.atomic():
        consultancy = ConsultancyProject.objects.create(
            faculty_user_id=faculty_user_id,
            department_id=department_id,
            title=title,
            client_name=client_name,
            client_details=client_details,
            scope=scope,
            deliverables=deliverables,
            duration_months=duration_months,
            financial_terms=financial_terms,
            budget_amount=budget_dec,
            requires_hod_review=requires_hod_review,
            is_strategic=is_strategic,
            start_date=start_date,
            end_date=end_date,
            status=ConsultancyStatus.SUBMITTED.value,
        )

        log_audit(
            record_type="consultancy",
            record_id=consultancy.id,
            action="register_consultancy",
            from_status=ConsultancyStatus.DRAFT.value,
            to_status=ConsultancyStatus.SUBMITTED.value,
            principal=principal,
            remarks="Consultancy registered by faculty",
        )

        create_notification(
            recipient_user_id=faculty_user_id,
            category="consultancy",
            title="Consultancy Registered",
            message=f"Consultancy '{title}' for client '{client_name}' registered and submitted.",
            record_type="consultancy",
            record_id=consultancy.id,
        )

    return consultancy


def transition_consultancy(
    *,
    consultancy_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
) -> ConsultancyProject:
    """Transition consultancy state along CW-RSPC-02."""
    with transaction.atomic():
        consultancy = ConsultancyProject.objects.select_for_update().get(pk=consultancy_id)
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "budget_amount": consultancy.budget_amount,
            "is_strategic": consultancy.is_strategic,
            "is_eligible": is_eligible,
        }

        validate_transition(
            transitions=CONSULTANCY_TRANSITIONS,
            from_state=consultancy.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"Consultancy #{consultancy.id}",
        )

        frm = consultancy.status
        consultancy.status = to_status
        consultancy.save(update_fields=["status", "updated_at"])

        log_audit(
            record_type="consultancy",
            record_id=consultancy.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        create_notification(
            recipient_user_id=consultancy.faculty_user_id,
            category="consultancy",
            title=f"Consultancy Status: {to_status}",
            message=f"Consultancy '{consultancy.title}' moved to {to_status}. Remarks: {remarks}",
            record_type="consultancy",
            record_id=consultancy.id,
        )

        if to_status == ConsultancyStatus.APPROVED.value:
            code = f"CP-{consultancy.id:04d}"
            RSPCProject.objects.get_or_create(
                project_code=code,
                defaults={
                    "title": consultancy.title,
                    "project_type": "consultancy",
                    "pi_user_id": consultancy.faculty_user_id,
                    "department_id": consultancy.department_id,
                    "funding_source": consultancy.client_name,
                    "sanctioned_budget": consultancy.budget_amount,
                    "utilized_budget": Decimal("0.00"),
                    "status": ProjectLifecycleStatus.ACTIVE.value,
                    "consultancy": consultancy,
                },
            )

    return consultancy


def record_consultancy_settlement(
    *,
    consultancy_id: int,
    milestone_name: str,
    deliverable_description: str = "",
    amount_due: Decimal | float | str = 0,
    amount_received: Decimal | float | str = 0,
    settlement_status: str = "pending",
    deliverable_status: str = "pending",
    principal: Any = None,
) -> ConsultancyMilestoneSettlement:
    """Record milestone settlements and deliverables (UC-008)."""
    with transaction.atomic():
        consultancy = ConsultancyProject.objects.get(pk=consultancy_id)
        settlement = ConsultancyMilestoneSettlement.objects.create(
            consultancy=consultancy,
            milestone_name=milestone_name,
            deliverable_description=deliverable_description,
            amount_due=Decimal(str(amount_due)),
            amount_received=Decimal(str(amount_received)),
            settlement_status=settlement_status,
            deliverable_status=deliverable_status,
        )
        log_audit(
            record_type="consultancy_settlement",
            record_id=settlement.id,
            action="record_settlement",
            principal=principal,
            remarks=f"Settlement recorded for {milestone_name}",
        )
    return settlement


# ---------------------------------------------------------------------------
# 3. Project Lifecycle Services (UC-001, UC-021, BR-RSPC-065)
# ---------------------------------------------------------------------------
def update_project_lifecycle(
    *,
    project_id: int,
    milestones: list | None = None,
    progress_info: str | None = None,
    principal: Any = None,
) -> RSPCProject:
    """Faculty updates ongoing project details, milestones, or progress (UC-021, BR-RSPC-065)."""
    with transaction.atomic():
        project = RSPCProject.objects.select_for_update().get(pk=project_id)

        # BR-RSPC-065: Check lifecycle editability
        if project.status in (
            ProjectLifecycleStatus.ARCHIVED.value,
            ProjectLifecycleStatus.COMPLETED.value,
        ):
            raise LifecycleNotPermittedError(project.status, "update")

        update_fields = ["updated_at"]
        if milestones is not None:
            project.milestones = milestones
            update_fields.append("milestones")
        if progress_info is not None:
            project.progress_info = progress_info
            update_fields.append("progress_info")

        project.save(update_fields=update_fields)

        log_audit(
            record_type="project",
            record_id=project.id,
            action="update_lifecycle_info",
            from_status=project.status,
            to_status=project.status,
            principal=principal,
            remarks="Project lifecycle info updated by faculty",
        )

    return project


# ---------------------------------------------------------------------------
# 4. Project Staff Appointment Services (UC-009, 010, 022, 023, CW-RSPC-03)
# ---------------------------------------------------------------------------
def request_staff_appointment(
    *,
    project_id: int,
    position_title: str,
    stipend_amount: Decimal | float | str,
    duration_months: int,
    advertisement_details: str = "",
    principal: Any = None,
) -> StaffAppointmentRequest:
    """Faculty requests project-based staff appointment (UC-009, BR-RSPC-026, BR-RSPC-058)."""
    with transaction.atomic():
        project = RSPCProject.objects.get(pk=project_id)
        user_id = getattr(principal, "user_id", project.pi_user_id)

        req = StaffAppointmentRequest.objects.create(
            project=project,
            faculty_user_id=user_id,
            position_title=position_title,
            stipend_amount=Decimal(str(stipend_amount)),
            duration_months=duration_months,
            advertisement_details=advertisement_details,
            status=StaffAppointmentStatus.REQUESTED.value,
        )

        log_audit(
            record_type="staff_appointment",
            record_id=req.id,
            action="request_staff",
            from_status=StaffAppointmentStatus.DRAFT.value,
            to_status=StaffAppointmentStatus.REQUESTED.value,
            principal=principal,
            remarks=f"Staff appointment requested for {position_title}",
        )

        create_notification(
            recipient_user_id=user_id,
            category="staff",
            title="Staff Appointment Requested",
            message=f"Staff appointment request for '{position_title}' submitted.",
            record_type="staff_appointment",
            record_id=req.id,
        )

    return req


def transition_staff_appointment(
    *,
    appointment_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
    recommendation: str = "",
    recommended_candidate_name: str = "",
    application_records: list | None = None,
    selection_committee_records: list | None = None,
) -> StaffAppointmentRequest:
    """Transition staff appointment along CW-RSPC-03."""
    with transaction.atomic():
        req = StaffAppointmentRequest.objects.select_for_update().get(pk=appointment_id)
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "is_eligible": is_eligible,
            "recommendation": recommendation or req.recommendation,
        }

        validate_transition(
            transitions=STAFF_TRANSITIONS,
            from_state=req.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"StaffAppointment #{req.id}",
        )

        frm = req.status
        req.status = to_status
        update_fields = ["status", "updated_at"]

        if recommendation:
            req.recommendation = recommendation
            update_fields.append("recommendation")
        if recommended_candidate_name:
            req.recommended_candidate_name = recommended_candidate_name
            update_fields.append("recommended_candidate_name")
        if application_records is not None:
            req.application_records = application_records
            update_fields.append("application_records")
        if selection_committee_records is not None:
            req.selection_committee_records = selection_committee_records
            update_fields.append("selection_committee_records")

        req.save(update_fields=update_fields)

        log_audit(
            record_type="staff_appointment",
            record_id=req.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        create_notification(
            recipient_user_id=req.faculty_user_id,
            category="staff",
            title=f"Staff Appointment Status: {to_status}",
            message=f"Staff request for '{req.position_title}' moved to {to_status}.",
            record_type="staff_appointment",
            record_id=req.id,
        )

    return req


# ---------------------------------------------------------------------------
# 5. Financial & Fund Management Services (UC-011, 012, 024, CW-RSPC-04)
# ---------------------------------------------------------------------------
def submit_financial_request(
    *,
    project_id: int,
    request_type: str,
    amount: Decimal | float | str,
    budget_head: str,
    description: str,
    principal: Any = None,
) -> FinancialRequest:
    """Faculty submits fund utilization or expenditure request (UC-011, BR-RSPC-059)."""
    with transaction.atomic():
        project = RSPCProject.objects.select_for_update().get(pk=project_id)
        amount_dec = Decimal(str(amount))
        user_id = getattr(principal, "user_id", project.pi_user_id)

        # Validate against available budget (BR-RSPC-035/059)
        if amount_dec > project.available_budget:
            raise BudgetExceededError(float(amount_dec), float(project.available_budget))

        req = FinancialRequest.objects.create(
            project=project,
            faculty_user_id=user_id,
            request_type=request_type,
            amount=amount_dec,
            budget_head=budget_head,
            description=description,
            status=FinancialRequestStatus.SUBMITTED.value,
        )

        log_audit(
            record_type="financial_request",
            record_id=req.id,
            action="submit_financial_request",
            from_status=FinancialRequestStatus.DRAFT.value,
            to_status=FinancialRequestStatus.SUBMITTED.value,
            principal=principal,
            remarks=f"Financial request of ₹{amount_dec} submitted under {budget_head}",
        )

        create_notification(
            recipient_user_id=user_id,
            category="finance",
            title="Financial Request Submitted",
            message=f"Request of ₹{amount_dec} for '{project.project_code}' submitted.",
            record_type="financial_request",
            record_id=req.id,
        )

    return req


def transition_financial_request(
    *,
    request_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
) -> FinancialRequest:
    """Transition financial request along CW-RSPC-04."""
    with transaction.atomic():
        req = FinancialRequest.objects.select_for_update().get(pk=request_id)
        project = req.project
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "amount": req.amount,
            "available_budget": project.available_budget,
            "is_eligible": is_eligible,
        }

        validate_transition(
            transitions=FINANCE_TRANSITIONS,
            from_state=req.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"FinancialRequest #{req.id}",
        )

        frm = req.status
        req.status = to_status
        req.save(update_fields=["status", "updated_at"])

        # When approved, update utilized budget
        if to_status == FinancialRequestStatus.APPROVED.value:
            project.utilized_budget += req.amount
            project.save(update_fields=["utilized_budget", "updated_at"])

        log_audit(
            record_type="financial_request",
            record_id=req.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        create_notification(
            recipient_user_id=req.faculty_user_id,
            category="finance",
            title=f"Financial Request Status: {to_status}",
            message=f"Your {req.request_type} request for ₹{req.amount} is now {to_status}.",
            record_type="financial_request",
            record_id=req.id,
        )

    return req


# ---------------------------------------------------------------------------
# 6. Procurement Services (UC-013, 025, 026, CW-RSPC-05)
# ---------------------------------------------------------------------------
def submit_procurement_request(
    *,
    project_id: int,
    item_type: str,
    item_name: str,
    quantity: int,
    estimated_cost: Decimal | float | str,
    specifications: str = "",
    principal: Any = None,
) -> ProcurementRequest:
    """Faculty submits procurement request (UC-013, BR-RSPC-035)."""
    with transaction.atomic():
        project = RSPCProject.objects.select_for_update().get(pk=project_id)
        cost_dec = Decimal(str(estimated_cost))
        user_id = getattr(principal, "user_id", project.pi_user_id)

        # Budget validation against project budget (BR-RSPC-035)
        if cost_dec > project.available_budget:
            raise BudgetExceededError(float(cost_dec), float(project.available_budget))

        req = ProcurementRequest.objects.create(
            project=project,
            faculty_user_id=user_id,
            item_type=item_type,
            item_name=item_name,
            quantity=quantity,
            estimated_cost=cost_dec,
            specifications=specifications,
            budget_validation_passed=True,
            status=ProcurementStatus.SUBMITTED.value,
        )

        log_audit(
            record_type="procurement_request",
            record_id=req.id,
            action="submit_procurement",
            from_status=ProcurementStatus.DRAFT.value,
            to_status=ProcurementStatus.SUBMITTED.value,
            principal=principal,
            remarks=f"Procurement submitted for {quantity}x {item_name}",
        )

        create_notification(
            recipient_user_id=user_id,
            category="procurement",
            title="Procurement Request Submitted",
            message=f"Procurement request for '{item_name}' (₹{cost_dec}) submitted.",
            record_type="procurement_request",
            record_id=req.id,
        )

    return req


def transition_procurement_request(
    *,
    request_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
) -> ProcurementRequest:
    """Transition procurement request along CW-RSPC-05."""
    with transaction.atomic():
        req = ProcurementRequest.objects.select_for_update().get(pk=request_id)
        project = req.project
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "estimated_cost": req.estimated_cost,
            "amount": req.estimated_cost,
            "available_budget": project.available_budget,
            "is_eligible": is_eligible,
        }

        validate_transition(
            transitions=PROCUREMENT_TRANSITIONS,
            from_state=req.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"ProcurementRequest #{req.id}",
        )

        frm = req.status
        req.status = to_status
        req.save(update_fields=["status", "updated_at"])

        log_audit(
            record_type="procurement_request",
            record_id=req.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        create_notification(
            recipient_user_id=req.faculty_user_id,
            category="procurement",
            title=f"Procurement Status: {to_status}",
            message=f"Procurement request for '{req.item_name}' moved to {to_status}.",
            record_type="procurement_request",
            record_id=req.id,
        )

    return req


# ---------------------------------------------------------------------------
# 7. Progress & Utilization Reporting (UC-014, BR-RSPC-037)
# ---------------------------------------------------------------------------
def submit_progress_report(
    *,
    project_id: int,
    report_type: str,
    period_start: Any,
    period_end: Any,
    summary: str,
    expenditure_reported: Decimal | float | str = 0,
    principal: Any = None,
) -> ProgressReport:
    """Faculty submits periodic progress/utilization report (UC-014, BR-RSPC-037)."""
    with transaction.atomic():
        project = RSPCProject.objects.get(pk=project_id)
        user_id = getattr(principal, "user_id", project.pi_user_id)

        rep = ProgressReport.objects.create(
            project=project,
            faculty_user_id=user_id,
            report_type=report_type,
            period_start=period_start,
            period_end=period_end,
            summary=summary,
            expenditure_reported=Decimal(str(expenditure_reported)),
            status="submitted",
        )

        log_audit(
            record_type="progress_report",
            record_id=rep.id,
            action="submit_report",
            principal=principal,
            remarks=f"{report_type.capitalize()} report for {period_start} to {period_end}",
        )

        create_notification(
            recipient_user_id=user_id,
            category="report",
            title="Progress Report Submitted",
            message=f"{report_type.capitalize()} report for '{project.project_code}' recorded.",
            record_type="progress_report",
            record_id=rep.id,
        )

    return rep


# ---------------------------------------------------------------------------
# 8. Project Closure Services (UC-015, 027, 028, CW-RSPC-06, BR-RSPC-043)
# ---------------------------------------------------------------------------
def submit_project_closure(
    *,
    project_id: int,
    completion_report: str,
    financial_settlement_record: str = "",
    asset_declaration_record: str = "",
    principal: Any = None,
) -> ProjectClosureRecord:
    """Faculty submits project completion & closure record (UC-015, CW-RSPC-06)."""
    with transaction.atomic():
        project = RSPCProject.objects.select_for_update().get(pk=project_id)
        user_id = getattr(principal, "user_id", project.pi_user_id)

        if not completion_report.strip():
            raise MandatoryFieldMissingError(["completion_report"])

        closure, _ = ProjectClosureRecord.objects.update_or_create(
            project=project,
            defaults={
                "faculty_user_id": user_id,
                "completion_report": completion_report,
                "financial_settlement_record": financial_settlement_record,
                "asset_declaration_record": asset_declaration_record,
                "status": ClosureStatus.SUBMITTED.value,
            },
        )

        log_audit(
            record_type="project_closure",
            record_id=closure.id,
            action="submit_closure",
            from_status=ClosureStatus.DRAFT.value,
            to_status=ClosureStatus.SUBMITTED.value,
            principal=principal,
            remarks="Project closure and completion report submitted",
        )

        create_notification(
            recipient_user_id=user_id,
            category="closure",
            title="Project Closure Submitted",
            message=f"Closure record for '{project.project_code}' submitted for verification.",
            record_type="project_closure",
            record_id=closure.id,
        )

    return closure


def transition_project_closure(
    *,
    closure_id: int,
    to_status: str,
    principal: Any,
    remarks: str = "",
    is_eligible: bool = True,
    settlement_verified: bool = True,
    assets_verified: bool = True,
) -> ProjectClosureRecord:
    """Transition project closure along CW-RSPC-06 (BR-RSPC-043)."""
    with transaction.atomic():
        closure = ProjectClosureRecord.objects.select_for_update().get(pk=closure_id)
        project = closure.project
        actor_role = _determine_actor_role(principal)

        context = {
            "remarks": remarks,
            "completion_report": closure.completion_report,
            "is_eligible": is_eligible,
            "settlement_verified": settlement_verified,
            "assets_verified": assets_verified,
            "budget_amount": project.sanctioned_budget,
            "is_strategic": False,
        }

        validate_transition(
            transitions=CLOSURE_TRANSITIONS,
            from_state=closure.status,
            to_state=to_status,
            actor_role=actor_role,
            context=context,
            entity_name=f"ProjectClosure #{closure.id}",
        )

        frm = closure.status
        closure.status = to_status
        closure.settlement_verified = settlement_verified
        closure.assets_verified = assets_verified
        closure.save(
            update_fields=["status", "settlement_verified", "assets_verified", "updated_at"]
        )

        # When archived, archive the project with complete audit trail (BR-RSPC-043)
        if to_status == ClosureStatus.ARCHIVED.value:
            project.status = ProjectLifecycleStatus.ARCHIVED.value
            project.archived_at = timezone.now()
            project.save(update_fields=["status", "archived_at", "updated_at"])

        log_audit(
            record_type="project_closure",
            record_id=closure.id,
            action=f"transition_{to_status}",
            from_status=frm,
            to_status=to_status,
            principal=principal,
            remarks=remarks,
        )

        create_notification(
            recipient_user_id=closure.faculty_user_id,
            category="closure",
            title=f"Project Closure Status: {to_status}",
            message=f"Closure for '{project.project_code}' is now {to_status}. Remarks: {remarks}",
            record_type="project_closure",
            record_id=closure.id,
        )

    return closure


# ---------------------------------------------------------------------------
# 9. Role Sync & Integration Tracking Services (UC-018, 029, 030)
# ---------------------------------------------------------------------------
def sync_role_assignment(
    *,
    user_id: int,
    new_role: str,
    previous_role: str = "",
    source_mechanism: str = "Fusion Role Management",
    principal: Any = None,
) -> RSPCRoleSynchronizationLog:
    """Synchronize RSPC role assignment changes (UC-018, BR-RSPC-053, 054, 055)."""
    with transaction.atomic():
        sync_log = RSPCRoleSynchronizationLog.objects.create(
            user_id=user_id,
            previous_role=previous_role,
            new_role=new_role,
            source_mechanism=source_mechanism,
        )
        log_audit(
            record_type="role_sync",
            record_id=sync_log.id,
            action="sync_role",
            principal=principal,
            remarks=f"Role sync {user_id}: {previous_role} -> {new_role} via {source_mechanism}",
        )
    return sync_log


def record_agency_tracking(
    *,
    agency_name: str,
    external_reference_number: str,
    submission_status: str,
    disbursement_status: str,
    disbursement_amount: Decimal | float | str = 0,
    project_id: int | None = None,
    proposal_id: int | None = None,
    principal: Any = None,
) -> ExternalAgencyTracking:
    """Record external funding agency submission and disbursement status (UC-030, BR-RSPC-062)."""
    with transaction.atomic():
        tracking = ExternalAgencyTracking.objects.create(
            project_id=project_id,
            proposal_id=proposal_id,
            agency_name=agency_name,
            external_reference_number=external_reference_number,
            submission_status=submission_status,
            disbursement_status=disbursement_status,
            disbursement_amount=Decimal(str(disbursement_amount)),
            updated_by_actor=_determine_actor_role(principal),
        )
        log_audit(
            record_type="agency_tracking",
            record_id=tracking.id,
            action="update_agency_tracking",
            principal=principal,
            remarks=f"Agency update from {agency_name} for ref {external_reference_number}",
        )
    return tracking
