from django.apps import AppConfig


class HostelConfig(AppConfig):
    name = "modules.hostel"
    label = "hostel"
    verbose_name = "Hostel Management"

    def ready(self) -> None:
        pass
