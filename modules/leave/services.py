from modules.leave.models import LeaveApplication, LeaveBalance
from django.core.exceptions import ValidationError

def submit_leave_application(user, leave_type, start_date, end_date):
    user_id = getattr(user, "user_id", getattr(user, "id", user))
    if start_date > end_date:
        raise ValidationError("Start date cannot be after end date.")
    
    leave_application = LeaveApplication(
        user_id=int(user_id),
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        status='pending'
    )
    leave_application.save()
    return leave_application


def approve_leave_application(leave_application):
    leave_application.status = 'approved'
    leave_application.save()


def reject_leave_application(leave_application):
    leave_application.status = 'rejected'
    leave_application.save()
