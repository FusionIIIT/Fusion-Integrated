from modules.hr_eis.models import Leave, Employee


def create_leave(employee_id, start_date, end_date, reason):
    employee = Employee.objects.get(id=employee_id)
    leave = Leave.objects.create(employee=employee, start_date=start_date, end_date=end_date, reason=reason)
    return leave
