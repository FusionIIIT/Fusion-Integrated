from modules.hr_eis.models import Employee, Department
from modules.hr_eis.notifications import send_employee_added_email


def get_employee_by_id(employee_id):
    return Employee.objects.get(id=employee_id)


def create_employee(name, email, department_id):
    department = Department.objects.get(id=department_id)
    employee = Employee.objects.create(name=name, email=email, department=department)
    send_employee_added_email(name, department.name)
    return employee
