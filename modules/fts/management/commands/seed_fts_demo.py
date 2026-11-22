"""Seeds demonstration files and movements for FTS development."""
from django.core.management.base import BaseCommand

from modules.fts.services.files import create_file
from modules.fts.services.movements import forward_file


class Command(BaseCommand):
    help = "Seed demonstration files for development and testing"

    def handle(self, *args, **options):
        # Create a sample draft file
        draft = create_file(
            subject="Equipment Procurement for Computer Center",
            description="Requisition of 40 new lab workstations and network switches.",
            comment_text="Initial draft for department review and verification.",
            actor_user_id=101,
            actor_username="faculty_cse",
            actor_role="Assistant Professor",
            actor_kind="faculty",
            is_draft=True,
        )
        self.stdout.write(f"Created draft file: {draft.reference_number}")

        # Create an active circulated file
        circ = create_file(
            subject="Approval for Conference Travel Grant",
            description="Application for travel grant for IEEE International Conference.",
            comment_text="Submitting travel grant request for administrative approval.",
            actor_user_id=101,
            actor_username="faculty_cse",
            actor_role="Assistant Professor",
            actor_kind="faculty",
            is_draft=False,
            recipient_user_id=201,
            recipient_username="staff_admin",
            recipient_role="Junior Superintendent",
        )
        self.stdout.write(f"Created circulated file: {circ.reference_number}")

        # Forward file to next authority
        forward_file(
            file_id=circ.id,
            actor_user_id=201,
            actor_username="staff_admin",
            actor_role="Junior Superintendent",
            actor_kind="staff",
            to_user_id=301,
            to_username="dean_acad",
            to_role="Dean Academic",
            comment_text="Verified documents. Forwarded to Dean Academic for sanction.",
        )
        self.stdout.write(f"Forwarded file {circ.reference_number} to Dean Academic")
        self.stdout.write(self.style.SUCCESS("FTS demo seed completed successfully."))
