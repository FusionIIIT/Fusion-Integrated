from modules.hr_eis.models import LTC, Employee


def create_ltc(employee_id, amount, purpose):
    employee = Employee.objects.get(id=employee_id)
    ltc = LTC.objects.create(employee=employee, amount=amount, purpose=purpose)
    return ltc
