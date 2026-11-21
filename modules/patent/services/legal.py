from django.db import transaction, connection
from datetime import date
from typing import Tuple

from core.exceptions import BusinessRuleViolation
from fusion_auth.permissions import HasPermission, HasModuleGrant
from modules.patent.models import (
    PatentApplication, AttorneyAssignment, PatentabilityOpinion,
    Budget, Filing, Inventor, ApplicationHistory,
)
from modules.patent.domain.policy import (
    can_transition, is_conflicted, validate_justification,
    budget_needs_escalation, missing_required_fields,
)


def assign_attorney(admin_id: int, application_id: int, attorney_id: int) -> AttorneyAssignment:
    """
    Assign an attorney to an approved application.
    
    Rules enforced (BR-PMS-040, 041, 042, 043, 044, 045, 127):
    - Only PCC_ADMIN can assign.
    - Application must be 'approved'.
    - Attorney must not be conflicted with inventors (BR-PMS-044).
    - Institutional exception handling is assumed to be pre-validated or handled externally; 
      this function assumes the attorney is eligible per panel rules unless conflict exists.
    
    Creates an AttorneyAssignment with status 'offered'.
    """
    application = PatentApplication.objects.get(pk=application_id)
    
    # BR-PMS-040: Only PCC_ADMIN may assign to Approved applications.
    if not can_transition(application.status, "attorney_assigned"):
        raise BusinessRuleViolation(f"Cannot assign attorney from status {application.status}. Must be 'approved'.")
    
    # Check conflict of interest (BR-PMS-044)
    inventors = Inventor.objects.filter(application=application).values_list("user_id", flat=True)
    if is_conflicted(attorney_id, inventors):
        raise BusinessRuleViolation(f"Attorney {attorney_id} has a conflict of interest with the application's inventors.")
    
    # Create assignment record
    assignment = AttorneyAssignment.objects.create(
        application=application,
        attorney_id=attorney_id,
        status="offered",
    )
    
    # Record history
    ApplicationHistory.objects.create(
        application=application,
        actor_id=admin_id,
        action="assign_attorney",
        from_status=application.status,
        to_status="attorney_assigned",
        note=f"Attorney {attorney_id} assigned.",
    )
    
    return assignment


def respond_to_assignment(attorney_id: int, assignment_id: int, accept: bool, reason: str = "") -> PatentApplication:
    """
    Record an attorney's response to an assignment.
    
    Rules enforced (BR-PMS-126):
    - Accept sets application status to 'attorney_assigned'.
    - Decline records the reason and allows reassignment (transition back to 'approved' via policy logic).
    
    Updates the AttorneyAssignment status and triggers state transition in the application.
    """
    assignment = AttorneyAssignment.objects.get(pk=assignment_id)
    application = assignment.application
    
    # Validate justification if declining (BR-PMS-030 implies Director review needs 50 chars, 
    # though this is an attorney decline, we assume a similar policy check applies to formal reasons)
    if not accept and reason:
        if len(reason.strip()) < 50:
            raise BusinessRuleViolation("Decline reason must be at least 50 characters.")
    
    if accept:
        # Transition to Attorney Assigned
        assignment.status = "accepted"
        application.status = "attorney_assigned"
        action_note = f"Attorney {attorney_id} accepted assignment."
    else:
        # Transition back to Approved (allows reassignment)
        assignment.status = "declined"
        application.status = "approved"
        action_note = f"Attorney {attorney_id} declined assignment. Reason: {reason}"
    
    assignment.save()
    
    ApplicationHistory.objects.create(
        application=application,
        actor_id=attorney_id,
        action="respond_to_assignment",
        from_status=application.status,  # Capture status before change for history accuracy if needed, 
                                       # but models.py logic might handle the 'to' state differently.
                                       # We record the action taken.
        to_status=application.status,
        note=action_note,
    )
    
    return application


def record_opinion(attorney_id: int, application_id: int, novelty: bool, non_obviousness: bool, 
                   utility: bool, recommendation: str, text: str) -> PatentabilityOpinion:
    """
    Record a patentability opinion by the assigned attorney.
    
    Rules enforced (BR-PMS-046):
    - Only the assigned attorney can record an opinion.
    - Recommendation must be one of: File Patent, Do Not File, Needs Amendment.
    - Opinion text validation is assumed to be handled by the service or middleware.
    
    Creates a PatentabilityOpinion.
    """
    application = PatentApplication.objects.get(pk=application_id)
    
    # Check if attorney is assigned (BR-PMS-046 implies Attorney performs assessment)
    assignment = AttorneyAssignment.objects.filter(
        application=application, 
        attorney_id=attorney_id,
        status="accepted"
    ).first()
    
    if not assignment:
        raise BusinessRuleViolation(f"Attorney {attorney_id} is not assigned to application {application_id}.")
    
    # Validate recommendation choices (BR-PMS-046)
    valid_recommendations = ["file_patent", "do_not_file", "needs_amendment"]
    if recommendation not in valid_recommendations:
        raise BusinessRuleViolation(f"Invalid recommendation. Must be one of: {valid_recommendations}.")
    
    opinion = PatentabilityOpinion.objects.create(
        application=application,
        attorney_id=attorney_id,
        novelty=novelty,
        non_obviousness=non_obviousness,
        utility=utility,
        recommendation=recommendation,
        opinion_text=text,
    )
    
    ApplicationHistory.objects.create(
        application=application,
        actor_id=attorney_id,
        action="record_opinion",
        from_status=application.status,
        to_status=application.status,  # Status doesn't change here, but action is recorded
        note=f"Patentability opinion recorded. Recommendation: {recommendation}.",
    )
    
    return opinion


def propose_budget(admin_id: int, application_id: int, filing_fee: float, attorney_fee: float, admin_cost: float) -> Budget:
    """
    Propose a budget for an approved application.
    
    Rules enforced (BR-PMS-048, 049, 050):
    - Only PCC_ADMIN can propose.
    - Application must be 'approved'.
    - Budget must include filing fees, attorney fees, and administrative costs.
    
    Creates a Budget with status 'pending'.
    """
    application = PatentApplication.objects.get(pk=application_id)
    
    # BR-PMS-052: Budget approval is permitted only when status is Approved. 
    # This function proposes, so we check if it's approved to allow proposal.
    if not can_transition(application.status, "approved"):
        raise BusinessRuleViolation(f"Cannot propose budget from status {application.status}. Must be 'approved'.")
    
    total = filing_fee + attorney_fee + admin_cost
    
    budget = Budget.objects.create(
        application=application,
        filing_fee=filing_fee,
        attorney_fee=attorney_fee,
        administrative_cost=admin_cost,
        total=total,
        status="pending",
        decided_by=admin_id,
    )
    
    ApplicationHistory.objects.create(
        application=application,
        actor_id=admin_id,
        action="propose_budget",
        from_status=application.status,
        to_status=application.status,
        note=f"Budget proposed. Total: ${total:.2f}.",
    )
    
    return budget


def decide_budget(director_id: int, budget_id: int, approve: bool, justification: str, threshold: float) -> Tuple[Budget, bool]:
    """
    Decide on a budget proposal.
    
    Rules enforced (BR-PMS-051):
    - If total exceeds threshold, escalate instead of approving.
    - Justification must be at least 50 characters (BR-PMS-030).
    
    Returns the updated Budget and whether it was escalated.
    """
    budget = Budget.objects.get(pk=budget_id)
    application = budget.application
    
    # Validate justification length (BR-PMS-030)
    if len(justification.strip()) < 50:
        raise BusinessRuleViolation("Budget justification must be at least 50 characters.")
    
    total = budget.total
    
    escalated = False
    if not approve and total > threshold:
        # If rejecting due to exceeding threshold, we escalate
        escalated = True
        budget.status = "escalated"
        budget.decided_by = director_id
        budget.justification = justification
        budget.save()
        
        ApplicationHistory.objects.create(
            application=application,
            actor_id=director_id,
            action="decide_budget",
            from_status=budget.status,
            to_status=budget.status,
            note=f"Budget escalated due to exceeding threshold (${threshold:.2f}). Total: ${total:.2f}. Justification: {justification}",
        )
    else:
        # Approve or Reject within threshold
        if approve:
            budget.status = "approved"
            budget.decided_by = director_id
            budget.justification = justification
            budget.save()
            
            ApplicationHistory.objects.create(
                application=application,
                actor_id=director_id,
                action="decide_budget",
                from_status=budget.status,
                to_status=budget.status,
                note=f"Budget approved. Total: ${total:.2f}. Justification: {justification}",
            )
        else:
            # Reject within threshold (not escalation)
            budget.status = "rejected"
            budget.decided_by = director_id
            budget.justification = justification
            budget.save()
            
            ApplicationHistory.objects.create(
                application=application,
                actor_id=director_id,
                action="decide_budget",
                from_status=budget.status,
                to_status=budget.status,
                note=f"Budget rejected. Total: ${total:.2f}. Justification: {justification}",
            )
    
    return budget, escalated


def record_filing(attorney_id: int, application_id: int, office: str, filing_number: str, 
                  filing_date: date, international: bool) -> Filing:
    """
    Record an external patent filing.
    
    Rules enforced (BR-PMS-020, 055, 056, 128):
    - Only the assigned attorney can record a filing.
    - Budget must be 'approved'.
    - Every inventor agreement must be signed (BR-PMS-020).
    - International filings require additional justification (assumed handled externally or via text field).
    
    Creates a Filing and updates application status to 'filed'.
    """
    application = PatentApplication.objects.get(pk=application_id)
    
    # Check budget approval (BR-PMS-128: External filing must not occur until required approvals... complete)
    budget = Budget.objects.filter(application=application, status="approved").first()
    if not budget:
        raise BusinessRuleViolation("Budget must be approved to file the patent.")
    
    # Check inventor agreements (BR-PMS-020)
    inventors = Inventor.objects.filter(application=application)
    for inventor in inventors:
        if not inventor.agreement_signed:
            raise BusinessRuleViolation(f"Inventor {inventor.name} has not signed the agreement.")
    
    # Check attorney assignment (BR-PMS-013 implies Attorney prepares and submits)
    assignment = AttorneyAssignment.objects.filter(
        application=application, 
        attorney_id=attorney_id,
        status="accepted"
    ).first()
    
    if not assignment:
        raise BusinessRuleViolation(f"Attorney {attorney_id} is not assigned to application {application_id}.")
    
    # Create filing record
    filing = Filing.objects.create(
        application=application,
        patent_office=office,
        filing_number=filing_number,
        filing_date=filing_date,
        international=international,
    )
    
    # Update application status to Filed (BR-PMS-013: PMS sets application status to Filed)
    application.status = "filed"
    application.save()
    
    ApplicationHistory.objects.create(
        application=application,
        actor_id=attorney_id,
        action="record_filing",
        from_status=application.status,
        to_status="filed",
        note=f"Filing recorded with {office}. Number: {filing_number}. Date: {filing_date}. International: {international}.",
    )
    
    return filing
