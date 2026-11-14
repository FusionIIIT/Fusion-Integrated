from modules.hr_eis.models import CPDA, Employee


def create_cpda(employee_id, amount, purpose):
    employee = Employee.objects.get(id=employee_id)
    cpda = CPDA.objects.create(employee=employee, amount=amount, purpose=purpose)
    return cpda
