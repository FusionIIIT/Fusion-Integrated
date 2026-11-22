from django.core.management.base import BaseCommand

from modules.iaa.services import decisions


class Command(BaseCommand):
    help = "Escalate overdue approvals now, exactly as the beat task does (IAA-BR-401)."

    def handle(self, *args, **options):
        report = decisions.escalate_overdue()
        self.stdout.write(self.style.SUCCESS(f"IAA escalation: {report}"))
