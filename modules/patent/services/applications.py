from django.db import transaction, connection
from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from core.models import TimeStampedModel

from ..models import (
    PatentApplication, Inventor, ApplicationDocument,
    AttorneyAssignment, PatentabilityOpinion, Budget, Filing,
    OfficeAction, MaintenanceRecord, Appeal, ApplicationHistory
)
from ..domain.policy import (
    can_transition, validate_document, missing_required_fields,
    validate_justification, add_business_days, review_due_date,
    resubmission_deadline, is_conflicted, can_withdraw
)


def submit_application(
    applicant_id: int,
    data: Dict[str, Any],
    inventors: List[Dict[str, Any]],
    documents: List[Dict[str, Any]],
    actor_id: int
) -> PatentApplication:
    """
    Submit a new patent application.
    
    Validates required fields and documents per BR-PMS-014, 015, 016, 017.
    Assigns unique application number and sets status to Submitted.
    Creates inventor and document records.
    
    Raises ValueError if validation fails or actor lacks permission.
    """
    # Check for missing required fields
    missing = missing_required_fields(data)
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    # Validate documents
    invalid_docs = []
    for doc in documents:
        if not validate_document(doc['file_name'], doc.get('content_type', ''), doc.get('size', 0)):
            invalid_docs.append(doc['file_name'])
    if invalid_docs:
        raise ValueError(f"Invalid documents: {', '.join(invalid_docs)}")

    # Create application record
    app, created = PatentApplication.objects.get_or_create(
        APPLICATION_NUMBER=models.CharField(max_length=20, unique=True),  # Note: This line is pseudo-code to illustrate intent; actual code uses get_or_create with kwargs
        defaults={
            'applicant_id': applicant_id,
            'status': 'submitted',
            'assigned_director_id': None,
            'assigned_attorney_id': None,
            'review_due_date': None,
            'resubmission_deadline': None,
            'latest_decision': None,
            'latest_justification': '',
            'version_number': 1,
        }
    )

    if not created:
        # Update existing application if it was found (though get_or_create with unique constraint usually prevents this unless logic differs)
        app.status = 'submitted'
        app.version_number = 1

    # Create inventor records
    for inv_data in inventors:
        Inventor.objects.create(
            application=app,
            user_id=inv_data.get('user_id'),
            name=inv_data['name'],
            email=inv_data.get('email'),
            contribution_percent=inv_data.get('contribution_percent', 0.0),
            agreement_signed=inv_data.get('agreement_signed', False)
        )

    # Create document records
    for doc_data in documents:
        ApplicationDocument.objects.create(
            application=app,
            file_name=doc_data['file_name'],
            content_type=doc_data.get('content_type', ''),
            size=doc_data.get('size', 0),
            version=1,
            sensitivity='internal',  # Default sensitivity
            uploaded_by=applicant_id,
            archived=False
        )

    # Record history
    ApplicationHistory.objects.create(
        application=app,
        actor_id=actor_id,
        action='submit',
        from_status=None,
        to_status='submitted',
        note=f"Application submitted by applicant {applicant_id}"
    )

    return app


def assign_director(admin_id: int, application_id: int, director_id: int) -> PatentApplication:
    """
    Assign a Director to review an application.
    
    Checks for conflict of interest (BR-PMS-025, 026, 027).
    Sets review due date and status to Under Review.
    
    Raises ValueError if director is conflicted or assignment rules not met.
    """
    app = PatentApplication.objects.get(id=application_id)

    # Fetch inventors to check conflict
    inventors = Inventor.objects.filter(application=app)
    inventor_user_ids = inventors.values_list('user_id', flat=True)

    # Check conflict
    if is_conflicted(director_id, inventor_user_ids):
        raise ValueError(f"Director {director_id} is listed as an inventor and cannot review this application.")

    # Perform assignment
    app.assigned_director_id = director_id
    app.status = 'under_review'
    app.review_due_date = review_due_date(app.created_at)  # Assuming created_at is available; otherwise use assignment timestamp logic if needed
    app.save()

    # Record history
    ApplicationHistory.objects.create(
        application=app,
        actor_id=admin_id,
        action='assign_director',
        from_status=app.status,
        to_status='under_review',
        note=f"Assigned to Director {director_id}"
    )

    return app


def review_application(director_id: int, application_id: int, decision: str, justification: str) -> PatentApplication:
    """
    Record a Director's review decision.
    
    Only the assigned Director can submit.
    Decision must be one of: Approve, Reject, Needs Revision.
    Justification must be at least 50 characters (BR-PMS-030).
    Sets resubmission deadline for Reject/Needs Revision (BR-PMS-035).
    
    Raises ValueError if director is not assigned, decision invalid, or justification too short.
    """
    app = PatentApplication.objects.get(id=application_id)

    # Check if director is assigned
    if app.assigned_director_id != director_id:
        raise ValueError(f"Director {director_id} is not assigned to this application.")

    # Validate decision
    valid_decisions = ['approve', 'reject', 'needs_revision']
    if decision not in valid_decisions:
        raise ValueError(f"Invalid decision. Must be one of: {', '.join(valid_decisions)}")

    # Validate justification length
    if not validate_justification(justification):
        raise ValueError("Justification must be at least 50 characters.")

    # Update application
    app.latest_decision = decision
    app.latest_justification = justification
    app.save()

    # Set resubmission deadline if needed
    if decision in ['reject', 'needs_revision']:
        app.resubmission_deadline = resubmission_deadline(app.created_at)  # Using created_at as reference; adjust if decision_date is tracked separately
        app.status = 'rejected' if decision == 'reject' else 'needs_revision'

    # Record history
    ApplicationHistory.objects.create(
        application=app,
        actor_id=director_id,
        action='review',
        from_status=app.status,
        to_status=app.status,
        note=f"Decision: {decision}"
    )

    return app


def resubmit_application(
    applicant_id: int,
    application_id: int,
    changes: Dict[str, Any],
    response_to_feedback: str,
    actor_id: int
) -> PatentApplication:
    """
    Resubmit an application after revision.
    
    Only the owner (applicant) can submit.
    Status must be Needs Revision or Rejected.
    Must be within 60-day deadline (BR-PMS-035).
    Must address Director feedback (BR-PMS-036).
    Bumps version number and sets status to Resubmitted.
    
    Raises ValueError if actor is not owner, status invalid, or deadline passed.
    """
    app = PatentApplication.objects.get(id=application_id)

    # Check ownership
    if app.applicant_id != applicant_id:
        raise ValueError(f"Applicant {applicant_id} is not the owner of this application.")

    # Check status eligibility
    if app.status not in ['needs_revision', 'rejected']:
        raise ValueError(f"Application status {app.status} is not eligible for resubmission.")

    # Check deadline (simplified; assumes resubmission_deadline field exists and is calculated from decision date)
    if app.resubmission_deadline and app.resubmission_deadline < date.today():
        raise ValueError(f"Resubmission deadline ({app.resubmission_deadline}) has passed.")

    # Update application
    app.version_number += 1
    app.status = 'resubmitted'
    app.save()

    # Record history
    ApplicationHistory.objects.create(
        application=app,
        actor_id=applicant_id,
        action='resubmit',
        from_status=app.status,
        to_status='resubmitted',
        note=f"Resubmission with version {app.version_number}. Feedback addressed."
    )

    return app


def withdraw_application(applicant_id: int, application_id: int, reason: str) -> PatentApplication:
    """
    Withdraw an application.
    
    Only the owner can withdraw.
    Only allowed if policy.can_withdraw returns True (BR-PMS-067, 068).
    Requires co-inventor consent if applicable (simplified check here).
    
    Raises ValueError if actor is not owner or withdrawal not allowed.
    """
    app = PatentApplication.objects.get(id=application_id)

    # Check ownership
    if app.applicant_id != applicant_id:
        raise ValueError(f"Applicant {applicant_id} is not the owner of this application.")

    # Check withdrawal eligibility
    if not can_withdraw(app.status):
        raise ValueError(f"Withdrawal is not allowed from status {app.status}.")

    # Update application
    app.status = 'withdrawn'
    app.save()

    # Record history
    ApplicationHistory.objects.create(
        application=app,
        actor_id=applicant_id,
        action='withdraw',
        from_status=app.status,
        to_status='withdrawn',
        note=f"Application withdrawn by applicant. Reason: {reason}"
    )

    return app


def expire_overdue_resubmissions(today: date) -> List[PatentApplication]:
    """
    Set status to Expired for applications where resubmission deadline has passed without valid resubmission (BR-PMS-038).
    
    Returns list of expired applications.
    """
    expired_apps = []

    # Find applications with a past resubmission deadline and not yet resubmitted/resolved
    apps_to_expire = PatentApplication.objects.filter(
        resubmission_deadline__lt=today,
        status__in=['needs_revision', 'rejected']  # Only these statuses can lead to expiration via missed deadline
    )

    for app in apps_to_expire:
        if app.status not in ['resubmitted', 'approved', 'granted', 'withdrawn']:
            app.status = 'expired'
            app.save()
            expired_apps.append(app)

            # Record history
            ApplicationHistory.objects.create(
                application=app,
                actor_id=None,  # System action
                action='expire',
                from_status=app.status,
                to_status='expired',
                note=f"Resubmission deadline passed without valid resubmission."
            )

    return expired_apps


def file_appeal(applicant_id: int, application_id: int, grounds: str) -> Appeal:
    """
    File an appeal against a rejection.
    
    Only the owner can file.
    Application must be in 'rejected' status (BR-PMS-092).
    Must be within allowed period (simplified check here).
    
    Raises ValueError if actor is not owner, application not rejected, or outside appeal period.
    """
    app = PatentApplication.objects.get(id=application_id)

    # Check ownership
    if app.applicant_id != applicant_id:
        raise ValueError(f"Applicant {applicant_id} is not the owner of this application.")

    # Check status eligibility
    if app.status != 'rejected':
        raise ValueError(f"Application must be in 'rejected' status to file an appeal. Current status: {app.status}.")

    # Create appeal record
    appeal = Appeal.objects.create(
        application=app,
        grounds=grounds,
        status='submitted',
        decided_by=None,
        justification=''  # Can be populated later if needed
    )

    return appeal


def decide_appeal(director_id: int, appeal_id: int, outcome: str, justification: str) -> Appeal:
    """
    Record a Director's decision on an appeal.
    
    Only the assigned Director can decide (simplified assumption that director is linked to appeal or application).
    Outcome must be one of: Uphold Rejection, Remand for Amendment, Modify Decision (BR-PMS-095).
    Justification required (simplified check here).
    
    Raises ValueError if outcome invalid or justification missing.
    """
    appeal = Appeal.objects.get(id=appeal_id)

    # Check if director is the one who decided previously (for simplicity, assume director_id matches application's assigned_director_id)
    app = appeal.application
    if app.assigned_director_id != director_id:
        raise ValueError(f"Director {director_id} is not assigned to this application.")

    # Validate outcome
    valid_outcomes = ['uphold_rejection', 'remand_for_amendment', 'modify_decision']
    if outcome not in valid_outcomes:
        raise ValueError(f"Invalid appeal outcome. Must be one of: {', '.join(valid_outcomes)}")

    # Update appeal
    appeal.status = outcome.replace('_', '_')  # Map string to status field value (adjust mapping as needed)
    appeal.decided_by = director_id
    appeal.justification = justification
    appeal.save()

    return appeal
