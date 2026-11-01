from django.apps import AppConfig

class HostelConfig(AppConfig):
    name = 'modules.hostel'
    label = 'hostel'

    def ready(self):
        from modules.hostel.models import Hostel, WardenRoleBinding, CaretakerRoleBinding
        from django.db.models.signals import post_save
        from modules.hostel.signals import update_role_history

        for model in [Hostel, WardenRoleBinding, CaretakerRoleBinding]:
            post_save.connect(update_role_history, sender=model)
