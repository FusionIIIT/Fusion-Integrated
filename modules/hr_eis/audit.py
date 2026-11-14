from django.db.models.signals import post_save
from django.dispatch import receiver
from modules.hr_eis.models import Employee


@receiver(post_save, sender=Employee)
def log_employee_creation(sender, instance, created, **kwargs):
    if created:
        print(f'Employee {instance.name} created.')
