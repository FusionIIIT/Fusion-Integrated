from django.apps import AppConfig


class LmsConfig(AppConfig):
    name = "modules.lms"
    label = "lms"

    def ready(self):
        pass
