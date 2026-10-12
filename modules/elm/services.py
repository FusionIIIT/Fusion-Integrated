from .models import LeaveRequest, LeaveApproval

def create_leave_request(employee, leave_type, reason):
    leave_request = LeaveRequest(employee=employee, leave_type=leave_type, reason=reason)
    leave_request.save()
    return leave_request

def approve_leave_request(leave_request, approved_by):
    leave_request.approved_by = approved_by
    leave_request.status = 'approved'
    leave_request.save()
    return leave_request