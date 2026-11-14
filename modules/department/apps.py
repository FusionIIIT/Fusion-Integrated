from django.apps import AppConfig


class DepartmentConfig(AppConfig):
    name = "modules.department"
    label = "department"
    verbose_name = "Department"

    def ready(self) -> None:
        return None
