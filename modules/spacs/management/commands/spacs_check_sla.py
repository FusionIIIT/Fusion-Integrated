"""Management command to check and escalate overdue SPACS tasks."""

from django.core.management.base import BaseCommand

from modules.spacs.services.tasks import check_and_escalate_sla_tasks


class Command(BaseCommand):
    help = "Check and escalate pending SPACS verification and approval tasks beyond SLA."

    def add_arguments(self, parser):
        parser.add_argument(
            "--sla-hours",
            type=int,
            default=48,
            help="SLA threshold in hours (default: 48)",
        )

    def handle(self, *args, **options):
        sla_hours = options["sla_hours"]
        escalated = check_and_escalate_sla_tasks(sla_hours=sla_hours)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully evaluated tasks. Escalated {len(escalated)} overdue tasks."
            )
        )
