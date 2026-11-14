
from modules.hr_eis.models import Appraisal, Employee


def create_appraisal(employee_id, performance_score, feedback):
    employee = Employee.objects.get(id=employee_id)
    appraisal = Appraisal.objects.create(employee=employee, performance_score=performance_score, feedback=feedback)
    return appraisal
