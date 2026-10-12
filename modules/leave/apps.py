from django.apps import AppConfig


class LeaveConfig(AppConfig):
    name = "modules.leave"
    label = "leave"

    def ready(self):
        from . import events  # noqa: F401
