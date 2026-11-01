from django.apps import AppConfig


class EmployeeLeaveConfig(AppConfig):
    name = "modules.employee_leave"
    label = "employee_leave"
    verbose_name = "Employee Leave Management"
    default_auto_field = "django.db.models.BigAutoField"
