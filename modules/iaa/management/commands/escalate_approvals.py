from django.core.management.base import BaseCommand
from modules.iaa.services.iaa import escalate_overdue_approvals

class Command(BaseCommand):
    help="Process configured overdue IAA approval steps."
    def handle(self,*args,**options):
        count=escalate_overdue_approvals()
        self.stdout.write(self.style.SUCCESS(f"Escalated {count} overdue IAA approval(s)."))
