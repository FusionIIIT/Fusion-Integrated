from modules.leave.models import LeaveApplication, LeaveBalance

def submit_leave_application(employee, leave_type, start_date, end_date):
    leave_application = LeaveApplication(
        employee=employee,
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
