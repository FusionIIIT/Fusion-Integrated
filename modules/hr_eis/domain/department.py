from modules.hr_eis.services.department import get_department_by_id


def get_department_details(department_id):
    department = get_department_by_id(department_id)
    return {
        'id': department.id,
        'name': department.name,
        'location': department.location,
    }
