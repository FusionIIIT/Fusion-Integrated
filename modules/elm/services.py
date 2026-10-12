from .models import LeaveBalance, LeaveRequest

def apply_leave(user, leave_type, start_date, end_date):
    leave_request = LeaveRequest(user=user, leave_type=leave_type, start_date=start_date, end_date=end_date)
    leave_request.save()

def approve_leave(leave_request):
    leave_request.status = LeaveRequest.STATUS_APPROVED
    leave_request.save()

def reject_leave(leave_request):
    leave_request.status = LeaveRequest.STATUS_REJECTED
    leave_request.save()