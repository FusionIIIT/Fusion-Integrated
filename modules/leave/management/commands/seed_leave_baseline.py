from datetime import date

from django.core.management.base import BaseCommand

from modules.leave.services import policy as policy_svc


class Command(BaseCommand):
    help = "Publish the study-baseline leave policy and empty holiday calendar if none is effective."

    def handle(self, *args, **options):
        policy_svc.seed_baseline(year=date.today().year)
        self.stdout.write("Leave baseline policy and calendar are effective.")
