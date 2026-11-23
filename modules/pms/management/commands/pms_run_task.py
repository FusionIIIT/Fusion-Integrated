from django.core.management.base import BaseCommand

TASKS = ("deliver_notifications", "process_deadlines", "auto_route_submissions",
         "run_scheduled_reports")


class Command(BaseCommand):
    help = "Run one of PMS's scheduled tasks now, in this process, and print what it did."

    def add_arguments(self, parser):
        parser.add_argument("--task", required=True, choices=TASKS)

    def handle(self, *args, task, **opts):
        from modules.pms import tasks

        result = getattr(tasks, task)()
        self.stdout.write(f"pms.{task}: {result}")
