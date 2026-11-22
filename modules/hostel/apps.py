from django.apps import AppConfig


class HostelConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "modules.hostel"
    label = "hostel"
    verbose_name = "Hostel Management"
