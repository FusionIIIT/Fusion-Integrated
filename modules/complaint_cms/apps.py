from django.apps import AppConfig

class ComplaintCmsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'modules.complaint_cms'
    label = 'complaint_cms'
    verbose_name = 'Complaint Management System'