"""Seed repeatable CSE records for local DEPT demonstrations."""

from datetime import time

from django.core.management.base import BaseCommand
from django.db import transaction

from modules.dept.models import Announcement, Department, InventoryItem, LabResource, TimetableSlot


class Command(BaseCommand):
    help = "Load idempotent CSE DEPT demo records (local development only)"

    @transaction.atomic
    def handle(self, *args, **options):
        department, _ = Department.objects.update_or_create(
            code="CSE",
            defaults={
                "name": "Computer Science and Engineering",
                "general_info": {
                    "description": "Computer Science and Engineering department demo profile.",
                    "email": "cse@example.invalid",
                    "office": "CSE Main Office",
                },
                "official_info": {},
            },
        )
        Announcement.objects.update_or_create(
            department=department,
            title="Welcome to the CSE department",
            defaults={
                "author_user_id": 5328,
                "body": "This is a local demonstration announcement for CSE students and faculty.",
                "target_roles": ["student", "faculty"],
                "published": True,
                "hidden": False,
                "deleted_at": None,
            },
        )
        InventoryItem.objects.update_or_create(
            department=department,
            name="HDMI cable",
            defaults={
                "description": "Demo stock item for testing department inventory and requests.",
                "on_hand": 12,
                "reserved": 0,
                "active": True,
            },
        )
        TimetableSlot.objects.update_or_create(
            department=department,
            title="CSE Systems Lab",
            weekday=1,
            starts_at=time(9, 0),
            defaults={
                "cohort": "CSE-2026",
                "resource": "Systems Lab",
                "ends_at": time(10, 30),
                "instructor_user_id": 5328,
            },
        )
        LabResource.objects.update_or_create(
            department=department,
            name="Systems Lab",
            defaults={
                "location": "CSE Block, Room 101",
                "details": {"capacity": 30, "availability": "Weekdays"},
                "active": True,
            },
        )
        self.stdout.write(self.style.SUCCESS("CSE DEPT demo records loaded"))
