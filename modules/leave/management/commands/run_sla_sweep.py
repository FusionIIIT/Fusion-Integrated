"""Run the SLA sweep by hand (EL-UC-021).

    manage.py run_sla_sweep
"""
from django.core.management.base import BaseCommand

from modules.leave.selectors import sla as sla_selector
from modules.leave.services import sla as sla_service


class Command(BaseCommand):
    help = "Remind and escalate the leave tasks still waiting past their threshold"

    def handle(self, *args, **opts):
        waiting = sla_selector.waiting()
        self.stdout.write(f"  actionable tasks  {len(waiting)}")
        report = sla_service.sweep()
        self.stdout.write(f"  reminded          {report['reminded']}")
        self.stdout.write(f"  escalated         {report['escalated']}")
        self.stdout.write(f"  rerouted          {report['rerouted']}")
        self.stdout.write(f"  skipped           {report['skipped']} "
                          f"(no threshold configured, or no longer pending)")
        if report["skipped"] and not sla_selector.reminders_logged():
            self.stdout.write(self.style.WARNING(
                "  no SLA threshold is configured yet — "
                "run 'manage.py seed_leave_policy'"))
