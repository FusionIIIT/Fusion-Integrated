from django.apps import AppConfig

class EmployeeLeaveManagementConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.employee_leave_management'

    def ready(self):
        # Import necessary components/checks when ready
        pass
