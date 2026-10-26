"""Leave Elm module app configuration."""
from django.apps import AppConfig


class LeaveElmConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.leave_elm'
    verbose_name = 'Leave Management'
