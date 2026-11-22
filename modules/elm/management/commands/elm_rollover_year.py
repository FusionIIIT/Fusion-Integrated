import json

from django.core.management.base import BaseCommand
from rest_framework.exceptions import ValidationError

from modules.elm.models import LeaveBalance
from modules.elm.year_end import rollover_employee


class Command(BaseCommand):
    help = "Process leave rollover for a specific year"

    def add_arguments(self, parser):
        parser.add_argument("--year", type=int, required=True)
        parser.add_argument("--employee", type=int)

    def handle(self, *args, **options):
        year = options["year"]
        employee_id = options["employee"]
        results = []
        exceptions = []

        if employee_id:
            employees = [employee_id]
        else:
            employees = list(
                LeaveBalance.objects.filter(year=year)
                .order_by("employee")
                .values_list("employee", flat=True)
                .distinct()
            )

        for emp in employees:
            try:
                status = rollover_employee(emp, year, None)
                results.append(status)
            except ValidationError as exc:
                exceptions.append({"employee": emp, "error": str(exc.detail)})

        output = {"year": year, "results": results, "exceptions": exceptions}
        self.stdout.write(json.dumps(output, indent=2))
