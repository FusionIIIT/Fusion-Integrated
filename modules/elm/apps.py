from django.apps import AppConfig


class ElmConfig(AppConfig):
    name = "modules.elm"
    label = "elm"

    def ready(self):
        # Import any necessary modules or functions here
        pass
