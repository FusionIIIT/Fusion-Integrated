from django.apps import AppConfig


class SuperAdminConfig(AppConfig):
    name = "modules.super_admin"
    label = "super_admin"
    verbose_name = "Super Admin"

    def ready(self):
        pass
