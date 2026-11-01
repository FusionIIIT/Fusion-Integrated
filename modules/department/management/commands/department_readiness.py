from django.core.management.base import BaseCommand

from modules.department.models import Department
from modules.department.selectors.role_assignments import current_holder


class Command(BaseCommand):
    help = "Report department roles with no current holder"

    def handle(self, *args, **options):
        vacant_roles = []
        departments = Department.objects.filter(is_active=True).order_by('code')

        for dept in departments:
            for role in ("hod", "dept_admin"):
                if current_holder(dept, role) is None:
                    vacant_roles.append(f"{dept.code}: {role} is vacant")

        if vacant_roles:
            for message in vacant_roles:
                self.stdout.write(message)
        else:
            self.stdout.write("All department roles are filled")
