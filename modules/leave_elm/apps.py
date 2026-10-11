from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

class LeaveElmConfig(AppConfig):
    name = 'modules.leave_elm'
    label = 'leave_elm'
    verbose_name = _('Employee Leave Management')
    default_auto_field = 'django.db.models.BigAutoField'