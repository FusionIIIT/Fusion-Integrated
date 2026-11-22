"""Seed demonstration files for File Tracking System."""

from django.core.management.base import BaseCommand

from modules.filetracking.models import TrackedFile
from modules.filetracking.services.files import create_file, forward_file


class Command(BaseCommand):
    help = "Seed demo files for File Tracking System."

    def handle(self, *args, **options):
        if TrackedFile.objects.exists():
            self.stdout.write("FileTracking demo data already exists.")
            return

        # 1. Draft file
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Proposal for High Performance Computing Cluster",
            initial_comment="Drafting preliminary proposal for departmental review.",
            is_draft=True,
        )

        # 2. Circulating file
        f2 = create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Curriculum Revision for Computer Science 2026",
            initial_comment="Submitted updated syllabus for approval by Dean Academic.",
            is_draft=False,
            recipient_user_id=2,
            recipient_designation="Dean Academic",
        )

        # 3. Multi-hop circulating file
        forward_file(
            file_id=f2.id,
            actor_user_id=2,
            actor_designation="Dean Academic",
            recipient_user_id=3,
            recipient_designation="placement_chairman",
            comment="Forwarded for placement committee review and feedback.",
        )

        self.stdout.write(self.style.SUCCESS("Successfully seeded FileTracking demo data."))
