from django.db import transaction
from core.api.exceptions import BadRequestError, ConflictError
from modules.leave.domain.state_machine import validate_transition
from modules.leave.models import LeaveApplication, LeaveBalance, LeaveLedgerEntry, LeaveActionHistory
from modules.leave.selectors.applications import get_application_by_id
from modules.leave.services.notifications import enqueue as enqueue_notification

@transaction.atomic
def review_by_unit_head(reviewer_user_id: int, application_id: int, recommended: bool, remarks: str = "") -> LeaveApplication:
    application = get_application_by_id(application_id)
    
    if application.category in ("CL", "RH"):
        if recommended:
            application.status = "approved"
            # Deduct balance and create ledger entry
            leave_balance = LeaveBalance.objects.get(employee=application.employee, leave_type=application.leave_type)
            leave_balance.balance -= application.days
            leave_balance.save()
            LeaveLedgerEntry.objects.create(
                employee=application.employee,
                leave_type=application.leave_type,
                days=application.days,
                entry_type="debit",
                remarks=remarks
            )
        else:
            application.status = "rejected"
        
        # Record action history
        LeaveActionHistory.objects.create(
            user_id=reviewer_user_id,
            application_id=application_id,
            action="unit_head_review",
            status=application.status,
            remarks=remarks
        )
    elif application.category in ("SCL", "EL", "COL", "VL"):
        application.unit_head_recommended = recommended
        application.unit_head_remarks = remarks
        
        if recommended:
            application.next_authority = "establishment_review"
        else:
            application.next_authority = None  # Not a rejection, just record the recommendation
        
        LeaveActionHistory.objects.create(
            user_id=reviewer_user_id,
            application_id=application_id,
            action="unit_head_review",
            status=application.status,
            remarks=remarks
        )
    
    application.save()
    enqueue_notification(application)
    return application

@transaction.atomic
def verify_by_establishment(reviewer_user_id: int, application_id: int, remarks: str = "") -> LeaveApplication:
    application = get_application_by_id(application_id)
    
    if application.next_authority == "establishment_review":
        application.next_authority = "sanction_review"
        
        LeaveActionHistory.objects.create(
            user_id=reviewer_user_id,
            application_id=application_id,
            action="establishment_review",
            status=application.status,
            remarks=remarks
        )
    
    application.save()
    enqueue_notification(application)
    return application

@transaction.atomic
def sanction_application(sanctioner_user_id: int, application_id: int, decision: str, remarks: str = "") -> LeaveApplication:
    if decision not in ("approved", "rejected"):
        raise BadRequestError("Invalid decision. Must be 'approved' or 'rejected'")
    
    application = get_application_by_id(application_id)
    
    if decision == "approved":
        # Deduct balance and create ledger entry
        leave_balance = LeaveBalance.objects.get(employee=application.employee, leave_type=application.leave_type)
        leave_balance.balance -= application.days
        leave_balance.save()
        LeaveLedgerEntry.objects.create(
            employee=application.employee,
            leave_type=application.leave_type,
            days=application.days,
            entry_type="debit",
            remarks=remarks
        )
    
    application.status = decision
    
    # Record action history
    LeaveActionHistory.objects.create(
        user_id=sanctioner_user_id,
        application_id=application_id,
        action="sanction_review",
        status=application.status,
        remarks=remarks
    )
    
    application.save()
    enqueue_notification(application)
    return application

@transaction.atomic
def process_cancellation_decision(reviewer_user_id: int, application_id: int, decision: str, remarks: str = "") -> LeaveApplication:
    if decision not in ("approved", "rejected"):
        raise BadRequestError("Invalid decision. Must be 'approved' or 'rejected'")
    
    application = get_application_by_id(application_id)
    
    if decision == "approved":
        # Restore deducted balance and create ledger entry
        leave_balance = LeaveBalance.objects.get(employee=application.employee, leave_type=application.leave_type)
        leave_balance.balance += application.days
        leave_balance.save()
        LeaveLedgerEntry.objects.create(
            employee=application.employee,
            leave_type=application.leave_type,
            days=application.days,
            entry_type="reversal",
            remarks=remarks
        )
    
    application.status = decision
    
    # Record action history
    LeaveActionHistory.objects.create(
        user_id=reviewer_user_id,
        application_id=application_id,
        action="cancellation_review",
        status=application.status,
        remarks=remarks
    )
    
    application.save()
    enqueue_notification(application)
    return application