from modules.hr_eis.services.employee import get_employee_by_id


def get_employee_details(employee_id):
    employee = get_employee_by_id(employee_id)
    return {
        'id': employee.id,
        'name': employee.name,
        'email': employee.email,
        'department': employee.department.name,
    }
