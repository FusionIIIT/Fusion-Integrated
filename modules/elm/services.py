# modules/elm/services.py

from .models import LeaveType, LeaveBalance, LeaveRequest
from django.core.exceptions import ObjectDoesNotExist

def apply_for_leave(user, leave_type_id, start_date, end_date):
    try:
        leave_type = LeaveType.objects.get(id=leave_type_id)
    except ObjectDoesNotExist:
        raise Exception("Leave type does not exist")

    leave_balance = LeaveBalance.objects.filter(user=user, leave_type=leave_type).first()
    if not leave_balance or leave_balance.balance <= 0:
        raise Exception("Insufficient leave balance")

    leave_request = LeaveRequest.objects.create(user=user, leave_type=leave_type, start_date=start_date, end_date=end_date, status='PENDING')

    leave_balance.balance -= 1
    leave_balance.save()

    return leave_request

def approve_leave_request(leave_request_id):
    try:
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
    except ObjectDoesNotExist:
        raise Exception("Leave request does not exist")

    leave_request.status = 'APPROVED'
    leave_request.save()

    return leave_request

def reject_leave_request(leave_request_id):
    try:
        leave_request = LeaveRequest.objects.get(id=leave_request_id)
    except ObjectDoesNotExist:
        raise Exception("Leave request does not exist")

    leave_request.status = 'REJECTED'
    leave_request.save()

    return leave_request