from django.apps import AppConfig


class LeaveConfig(AppConfig):
    """Leave Management Module Application Config."""
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.leave'
    label = 'leave'

    def ready(self):
        """App ready hook."""
        pass