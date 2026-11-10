"""Unit tests for FTS Inbox/Outbox Selectors and Archival Services.

Tests FTS-UC-005, FTS-UC-007, and BR-FTS-012.
"""

import pytest

from modules.fts.domain.workflow import STATUS_ARCHIVED
from modules.fts.models import FTSComment, FTSFile, FTSMovement
from modules.fts.selectors.inbox_outbox import (
    get_user_inbox_files,
    get_user_outbox_files,
)
from modules.fts.services.archival import archive_file
from modules.fts.services.drafts import create_file_draft
from modules.fts.services.movements import forward_file


@pytest.mark.django_db
class TestInboxOutboxSelectors:
    """Tests for get_user_inbox_files and get_user_outbox_files (FTS-UC-005)."""

    def test_inbox_outbox_distribution(self):
        # 1. User A creates and forwards a file to User B
        draft1 = create_file_draft(
            creator_id="user_a",
            creator_role="Staff",
            subject="Project Proposal",
            initial_comment="Please review",
        )
        forward_file(
            file_id=draft1["file_id"],
            sender_id="user_a",
            sender_role="Staff",
            receiver_id="user_b",
            receiver_role="HOD",
            comment="Submitted for review",
        )

        # 2. Check User B's Inbox: must contain the forwarded file
        inbox_b = get_user_inbox_files(user_id="user_b")
        assert len(inbox_b) == 1
        assert inbox_b[0]["id"] == draft1["file_id"]

        # 3. Check User A's Outbox: must contain the forwarded file
        outbox_a = get_user_outbox_files(user_id="user_a")
        assert len(outbox_a) == 1
        assert outbox_a[0]["id"] == draft1["file_id"]

        # 4. Check User A's Inbox: should be empty
        inbox_a = get_user_inbox_files(user_id="user_a")
        assert len(inbox_a) == 0

    def test_drafts_excluded_from_inbox(self):
        # Drafts stay in draft selector, not in active inbox
        create_file_draft(
            creator_id="user_c",
            creator_role="Staff",
            subject="Draft in progress",
            initial_comment="Working on it",
        )
        assert len(get_user_inbox_files(user_id="user_c")) == 0


@pytest.mark.django_db
class TestArchivalService:
    """Tests for archive_file (FTS-UC-007, BR-FTS-012)."""

    def test_successful_archival_by_holder(self):
        draft = create_file_draft(
            creator_id="user_d",
            creator_role="Faculty",
            subject="Completed Task",
            initial_comment="All done",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_d",
            sender_role="Faculty",
            receiver_id="registrar_01",
            receiver_role="Registrar",
            comment="Final signoff needed",
        )

        result = archive_file(
            file_id=draft["file_id"],
            user_id="registrar_01",
            user_role="Registrar",
            remarks="Sanctioned and archived into institute record.",
        )

        assert result["status"] == STATUS_ARCHIVED

        # Verify DB
        file_obj = FTSFile.objects.get(id=draft["file_id"])
        assert file_obj.status == STATUS_ARCHIVED

        # Verify closing comment
        comment = FTSComment.objects.filter(file=file_obj).order_by("-created_at").first()
        assert comment.remarks == "Sanctioned and archived into institute record."

        # Verify movement
        assert FTSMovement.objects.filter(file=file_obj, action="archived").exists()

    def test_unauthorized_user_cannot_archive(self):
        draft = create_file_draft(
            creator_id="user_e",
            creator_role="Faculty",
            subject="Active Discussion",
            initial_comment="Notes",
        )
        forward_file(
            file_id=draft["file_id"],
            sender_id="user_e",
            sender_role="Faculty",
            receiver_id="user_f",
            receiver_role="Dean",
            comment="Review needed",
        )

        with pytest.raises(PermissionError, match="Only the creator or current holder"):
            archive_file(
                file_id=draft["file_id"],
                user_id="intruder_x",
                user_role="Staff",
                remarks="Malicious archive attempt",
            )
