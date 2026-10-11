from .models import LeaveRequest

def apply_for_leave(user, leave_type, start_date, end_date):
    leave_request = LeaveRequest(user=user, leave_type=leave_type, start_date=start_date, end_date=end_date)
    leave_request.save()
    return leave_request

def approve_leave(leave_request_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = 'Approved'
    leave_request.save()
    return leave_request

def reject_leave(leave_request_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = 'Rejected'
    leave_request.save()
    return leave_request