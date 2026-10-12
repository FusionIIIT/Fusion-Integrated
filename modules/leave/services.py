from .models import LeaveRequest


def create_leave_request(user, leave_type, start_date, end_date):
    leave_request = LeaveRequest(
        user=user,
        leave_type=leave_type,
        start_date=start_date,
        end_date=end_date
    )
    leave_request.save()
    return leave_request

def update_leave_request(leave_request_id, status):
    leave_request = LeaveRequest.objects.get(id=leave_request_id)
    leave_request.status = status
    leave_request.save()
    return leave_request
