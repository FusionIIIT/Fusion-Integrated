# modules/hr_eis/apps.py
from django.apps import AppConfig


class HrEisConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.hr_eis'
    verbose_name = 'HR and Employee Information System'