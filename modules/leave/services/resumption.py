from django.db import transaction
from datetime import date
from modules.leave.models import LeaveApplication, LeaveBalance, LeaveLedgerEntry

@transaction.atomic
def submit_resumption_declaration(user_id: int, application_id: int, resumption_date: date, remarks: str = "") -> LeaveApplication:
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status != "approved":
        raise ValueError("Leave application must be approved before submitting a resumption declaration.")
    
    if app.category not in ("EL", "COL", "VL"):
        raise ValueError("Invalid leave category for resumption declaration.")
    
    app.resumption_date = resumption_date
    app.status = "resumption_submitted"
    app.remarks = remarks
    app.save()
    
    return app

@transaction.atomic
def review_resumption_declaration(reviewer_user_id: int, application_id: int, remarks: str = "") -> LeaveApplication:
    app = LeaveApplication.objects.get(id=application_id)
    
    if app.status != "resumption_submitted":
        raise ValueError("Leave application must be in resumption submitted status for review.")
    
    if app.resumption_date < app.end_date + date(1, 1, 1):
        unused_days = (app.end_date - app.resumption_date).days + 1
        leave_balance = LeaveBalance.objects.get(employee_id=app.employee_id, leave_type=app.category)
        
        # Credit back unused days to LeaveBalance
        leave_balance.balance += unused_days
        leave_balance.save()
        
        # Create LeaveLedgerEntry for adjustment
        LeaveLedgerEntry.objects.create(
            employee_id=app.employee_id,
            leave_type=app.category,
            entry_type="adjustment",
            amount=unused_days * app.leave_type.rate,
            remarks=f"Resumption of {unused_days} days"
        )
    
    app.status = "closed"
    app.remarks = remarks
    app.save()
    
    return app