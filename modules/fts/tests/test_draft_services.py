"""Unit tests for FTS Draft Services and Selectors (FTS-UC-001, FTS-UC-002).

Validates database state transitions, mandatory initial comment, editing, and discarding.
"""

import pytest

from modules.fts.domain.workflow import STATUS_DRAFT, STATUS_IN_TRANSIT
from modules.fts.models import FTSComment, FTSFile, FTSMovement
from modules.fts.selectors.drafts import get_draft_by_id, get_user_draft_files
from modules.fts.services.drafts import (
    create_file_draft,
    discard_file_draft,
    update_file_draft,
)


@pytest.mark.django_db
class TestDraftCreationService:
    """Tests for create_file_draft (FTS-UC-001)."""

    def test_successful_draft_creation(self):
        result = create_file_draft(
            creator_id="emp_01",
            creator_role="Faculty",
            subject="Grant Application 2025",
            initial_comment="Submitting research proposal for approval.",
            priority="high",
            category="research",
            description="Detailed grant application payload.",
        )

        assert result["file_id"] is not None
        assert result["status"] == STATUS_DRAFT
        assert result["is_draft"] is True
        assert "FTS-" in result["uin"]

        # Verify DB records
        file_obj = FTSFile.objects.get(id=result["file_id"])
        assert file_obj.subject == "Grant Application 2025"
        assert file_obj.creator_id == "emp_01"
        assert file_obj.current_holder_id == "emp_01"

        # Verify initial movement
        assert FTSMovement.objects.filter(file=file_obj, action="created").exists()

        # Verify initial comment
        comment_obj = FTSComment.objects.get(file=file_obj)
        assert comment_obj.remarks == "Submitting research proposal for approval."
        assert comment_obj.author_id == "emp_01"

    def test_creation_fails_without_initial_comment(self):
        with pytest.raises(ValueError, match="Initial comment is mandatory"):
            create_file_draft(
                creator_id="emp_01",
                creator_role="Faculty",
                subject="Missing Remark File",
                initial_comment="   ",
            )


@pytest.mark.django_db
class TestDraftUpdateAndDiscard:
    """Tests for update_file_draft and discard_file_draft (FTS-UC-002)."""

    def test_creator_can_update_draft(self):
        created = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Initial Title",
            initial_comment="Initial remark",
        )

        updated = update_file_draft(
            file_id=created["file_id"],
            user_id="emp_01",
            subject="Updated Title",
            priority="urgent",
        )

        assert updated["subject"] == "Updated Title"
        refreshed = FTSFile.objects.get(id=created["file_id"])
        assert refreshed.subject == "Updated Title"
        assert refreshed.priority == "urgent"

    def test_non_creator_cannot_update_draft(self):
        created = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Initial Title",
            initial_comment="Initial remark",
        )

        with pytest.raises(PermissionError, match="Only the file creator"):
            update_file_draft(
                file_id=created["file_id"],
                user_id="emp_02",  # Different user
                subject="Hacked Title",
            )

    def test_active_file_cannot_be_updated_as_draft(self):
        created = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Circulating File",
            initial_comment="Moving",
        )
        file_obj = FTSFile.objects.get(id=created["file_id"])
        file_obj.status = STATUS_IN_TRANSIT
        file_obj.is_draft = False
        file_obj.save()

        with pytest.raises(PermissionError, match="Only files in draft status"):
            update_file_draft(
                file_id=created["file_id"],
                user_id="emp_01",
                subject="Attempted Edit",
            )

    def test_discard_draft_deletes_file(self):
        created = create_file_draft(
            creator_id="emp_01",
            creator_role="Staff",
            subject="Temporary Draft",
            initial_comment="Discard me",
        )

        result = discard_file_draft(file_id=created["file_id"], user_id="emp_01")
        assert result["status"] == "discarded"
        assert not FTSFile.objects.filter(id=created["file_id"]).exists()


@pytest.mark.django_db
class TestDraftSelectors:
    """Tests for get_user_draft_files and get_draft_by_id."""

    def test_get_user_draft_files(self):
        create_file_draft(
            creator_id="emp_user_a",
            creator_role="Staff",
            subject="Draft A1",
            initial_comment="First",
        )
        create_file_draft(
            creator_id="emp_user_a",
            creator_role="Staff",
            subject="Draft A2",
            initial_comment="Second",
        )
        create_file_draft(
            creator_id="emp_user_b",
            creator_role="Staff",
            subject="Draft B1",
            initial_comment="Other user",
        )

        drafts_a = get_user_draft_files(creator_id="emp_user_a")
        assert len(drafts_a) == 2
        subjects = [d["subject"] for d in drafts_a]
        assert "Draft A1" in subjects
        assert "Draft A2" in subjects

    def test_get_draft_by_id_isolated_per_user(self):
        created = create_file_draft(
            creator_id="emp_user_a",
            creator_role="Staff",
            subject="Secret Draft",
            initial_comment="Confidential",
        )

        # Owner gets the draft
        assert get_draft_by_id(created["file_id"], "emp_user_a") is not None
        # Non-owner cannot see it
        assert get_draft_by_id(created["file_id"], "emp_user_b") is None
