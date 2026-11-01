from django.apps import AppConfig


class ElmConfig(AppConfig):
    name = "modules.elm"
    label = "elm"

    def ready(self):
        # Import signals/handlers here if needed
        pass