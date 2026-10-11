from .domain.entities import LeaveRequestEntity
from .domain.state_machine import LeaveRequestStateMachine
from .models import LeaveRequest

def create_leave_request(user_id, leave_type, start_date, end_date, half_day):
    leave_request = LeaveRequest(
        user_id=user_id,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date,
        half_day=half_day,
        status='pending'
    )
    leave_request.save()
    return leave_request

def approve_leave_request(leave_request_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = 'approved'
    leave_request.save()

def reject_leave_request(leave_request_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = 'rejected'
    leave_request.save()

def cancel_leave_request(leave_request_id):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = 'cancelled'
    leave_request.save()
