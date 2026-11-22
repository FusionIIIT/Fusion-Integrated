"""Seed VMS initial test policies and records."""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from modules.vms.services.registration import request_or_create_visit
from modules.vms.services.security import add_to_blacklist


class Command(BaseCommand):
    help = "Seed initial VMS sample records and test policies."

    def handle(self, *args, **options):
        self.stdout.write("Seeding VMS sample data...")

        # 1. Seed Blacklist Entry
        bl = add_to_blacklist(
            id_type="aadhaar",
            id_number="999988887777",
            full_name="Banned Guest",
            phone="9876543210",
            reason="Violation of campus security policy",
            severity="critical",
        )
        self.stdout.write(f"Created blacklist entry: {bl.full_name}")

        # 2. Seed Pre-registered visit
        now = timezone.now()
        visit = request_or_create_visit(
            visitor_data={
                "first_name": "Ramesh",
                "last_name": "Sharma",
                "phone": "9123456780",
                "email": "ramesh.sharma@example.com",
                "id_type": "aadhaar",
                "id_number": "123456789012",
                "organization": "Tech Corp",
            },
            host_user_id=1,
            purpose="Guest Lecture in Computer Science",
            valid_from=now - timedelta(hours=1),
            valid_to=now + timedelta(hours=5),
            allowed_zones=["MAIN_GATE", "ACADEMIC_BLOCK"],
            visit_type="pre_registered",
        )
        self.stdout.write(f"Created sample visit: {visit.pass_number}")
        self.stdout.write(self.style.SUCCESS("VMS seeding complete!"))
