"""Seed initial catalog of academic and administrative role definitions."""
from django.core.management.base import BaseCommand

from modules.system_admin.constants import RoleCategory
from modules.system_admin.models import RoleDefinition

INITIAL_ROLES = [
    # Basic
    {"code": "student", "label": "Student", "category": RoleCategory.BASIC, "allowed_kinds": "student", "is_singular": False},
    {"code": "faculty", "label": "Faculty", "category": RoleCategory.BASIC, "allowed_kinds": "faculty", "is_singular": False},
    {"code": "staff", "label": "Staff", "category": RoleCategory.BASIC, "allowed_kinds": "staff", "is_singular": False},
    # Academic Ranks
    {"code": "professor", "label": "Professor", "category": RoleCategory.RANK, "allowed_kinds": "faculty", "is_singular": False},
    {"code": "associate_professor", "label": "Associate Professor", "category": RoleCategory.RANK, "allowed_kinds": "faculty", "is_singular": False},
    {"code": "assistant_professor", "label": "Assistant Professor", "category": RoleCategory.RANK, "allowed_kinds": "faculty", "is_singular": False},
    # Administrative Offices (Singular)
    {"code": "director", "label": "Director", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "dean_academic", "label": "Dean Academic", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "dean_students", "label": "Dean Students", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "dean_rd", "label": "Dean R&D", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "hod", "label": "Head of Department", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "warden", "label": "Hall Warden", "category": RoleCategory.OFFICE, "allowed_kinds": "faculty,staff", "is_singular": True, "is_time_bound": True},
    # Functional Roles
    {"code": "placement_chairman", "label": "Placement Chairman", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "pic_library", "label": "Professor In-Charge Library", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "faculty", "is_singular": True, "is_time_bound": True},
    {"code": "club_coordinator", "label": "Student Club Coordinator", "category": RoleCategory.FUNCTIONAL, "allowed_kinds": "student", "is_singular": False, "is_time_bound": True},
]


class Command(BaseCommand):
    help = "Seed initial role definitions into the catalog."

    def handle(self, *args, **options):
        created_count = 0
        for rdata in INITIAL_ROLES:
            _, created = RoleDefinition.objects.get_or_create(
                code=rdata["code"],
                defaults={
                    "label": rdata["label"],
                    "category": rdata["category"],
                    "allowed_kinds": rdata["allowed_kinds"],
                    "is_singular": rdata.get("is_singular", False),
                    "is_time_bound": rdata.get("is_time_bound", False),
                },
            )
            if created:
                created_count += 1
        self.stdout.write(self.style.SUCCESS(f"Seeded {created_count} role definitions."))
