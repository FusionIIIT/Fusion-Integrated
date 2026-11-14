from modules.hr_eis.models import Approval, Employee


def create_approval(employee_id, amount, purpose):
    employee = Employee.objects.get(id=employee_id)
    approval = Approval.objects.create(employee=employee, amount=amount, purpose=purpose)
    return approval
