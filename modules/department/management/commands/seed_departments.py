from django.core.management.base import BaseCommand
from django.db import transaction

from modules.department.models import Department

DEPARTMENTS = {
    "CSE": "Computer Science and Engineering",
    "ECE": "Electronics and Communication Engineering",
    "ME": "Mechanical Engineering",
    "Design": "Design",
    "NS": "Natural Sciences",
    "SM": "Smart Manufacturing",
    "LA": "Liberal Arts",
}


class Command(BaseCommand):
    help = "Create the institute's departments; never overwrites an existing one's details."

    @transaction.atomic
    def handle(self, *args, **options):
        created = sum(
            Department.objects.get_or_create(code=code, defaults={"name": name})[1]
            for code, name in DEPARTMENTS.items()
        )
        total = Department.objects.count()
        self.stdout.write(f"Seeded departments ({created} created, {total} total).")
