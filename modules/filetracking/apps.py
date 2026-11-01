from django.apps import AppConfig


class FileTrackingConfig(AppConfig):
    name = "modules.filetracking"
    label = "filetracking"
    verbose_name = "File Tracking System"

    def ready(self):
        pass

