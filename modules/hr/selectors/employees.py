from django.db.models import QuerySet

from modules.hr.models import EmployeeRecord


def visible_employee_records(principal) -> QuerySet[EmployeeRecord]:
    records = EmployeeRecord.objects.prefetch_related("leave_balances")
    if principal.has_permission("hr.employee.view"):
        return records
    return records.filter(user_id=principal.user_id)


def employee_record_for_user(*, user_id: int, principal) -> EmployeeRecord | None:
    return visible_employee_records(principal).filter(user_id=user_id).first()
