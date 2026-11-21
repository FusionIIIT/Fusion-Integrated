from modules.hr_eis.models.employees import Department

def get_department_by_id(department_id):
    return Department.objects.get(id=department_id)
