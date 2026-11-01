"""Unit tests for FTS pure Python domain layer.

Runs without DB or Django framework dependency.
Tests business rules BR-FTS-001 through BR-FTS-014 and workflows BW-FTS-01..08.
"""
import pytest

from modules.filetracking.domain import (
    ArchivalNotAllowedError,
    AttachmentInfo,
    DraftBoundaryViolationError,
    FileArchivedError,
    FileComposite,
    FileLifecycleState,
    InitialCommentRequiredError,
    InvalidReturnTargetError,
    MovementCommentRequiredError,
    MovementType,
    NotFileHolderError,
    SystemAdminOperationalActionBlockedError,
    UnauthorizedFileActionError,
)


class TestFileCreationAndDraftManagement:
    """FTS-UC-001, FTS-UC-002; BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-005."""

    def test_create_draft_success(self):
        file_obj = FileComposite.create_new_draft(
            subject="Purchase Requisition",
            description="Lab equipment purchase",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Please approve the requisition.",
            attachments=[AttachmentInfo(file_name="quotation.pdf", file_path="/files/1.pdf")],
        )
        assert file_obj.state == FileLifecycleState.DRAFT
        assert file_obj.creator_id == 101
        assert file_obj.owner_id == 101
        assert file_obj.current_holder_id == 101
        assert len(file_obj.comments) == 1
        assert file_obj.comments[0].comment_text == "Please approve the requisition."
        assert len(file_obj.attachments) == 1

    def test_create_file_missing_initial_comment_raises(self):
        with pytest.raises(InitialCommentRequiredError):
            FileComposite.create_new_draft(
                subject="Test",
                description="Test",
                creator_id=101,
                creator_role="faculty",
                initial_comment="",
            )

    def test_system_admin_cannot_create_operational_file(self):
        with pytest.raises(SystemAdminOperationalActionBlockedError):
            FileComposite.create_new_draft(
                subject="Test",
                description="Test",
                creator_id=1,
                creator_role="admin",
                initial_comment="Admin note",
                is_system_admin=True,
            )

    def test_edit_draft_success(self):
        file_obj = FileComposite.create_new_draft(
            subject="Original Subject",
            description="Original Description",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Original comment",
        )
        file_obj.edit_draft(
            actor_id=101,
            subject="Updated Subject",
            description="Updated Description",
            new_comment="Updated comment",
        )
        assert file_obj.subject == "Updated Subject"
        assert file_obj.description == "Updated Description"
        assert file_obj.comments[0].comment_text == "Updated comment"

    def test_other_user_cannot_edit_draft(self):
        file_obj = FileComposite.create_new_draft(
            subject="Subject",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Comment",
        )
        with pytest.raises(UnauthorizedFileActionError):
            file_obj.edit_draft(actor_id=102, subject="Hacked")

    def test_discard_draft_success(self):
        file_obj = FileComposite.create_new_draft(
            subject="Subject",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Comment",
        )
        # Should succeed without error
        file_obj.discard_draft(actor_id=101)


class TestFileMovement:
    """FTS-UC-003, FTS-UC-004; BR-FTS-006, BR-FTS-007, BR-FTS-008."""

    def test_forward_file_from_draft_enters_circulation(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Project Proposal",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Draft proposal",
        )
        m = file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="Submitting for HOD review.",
        )
        assert file_obj.state == FileLifecycleState.CIRCULATED
        assert file_obj.current_holder_id == 102
        assert len(file_obj.movements) == 1
        assert m.movement_type == MovementType.FORWARD
        assert m.receiver_id == 102
        assert len(file_obj.comments) == 2  # initial + forward comment

    def test_cannot_discard_circulated_file(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Project Proposal",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Draft proposal",
        )
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="Submitting.",
        )
        with pytest.raises(DraftBoundaryViolationError):
            file_obj.discard_draft(actor_id=101)

    def test_forward_requires_movement_comment(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Draft",
        )
        with pytest.raises(MovementCommentRequiredError):
            file_obj.forward(
                sender_id=101,
                sender_role="faculty",
                receiver_id=102,
                receiver_role="hod",
                comment="",
            )

    def test_non_holder_cannot_forward(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Draft",
        )
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="Submitting.",
        )
        # 101 is no longer holder; 102 is
        with pytest.raises(NotFileHolderError):
            file_obj.forward(
                sender_id=101,
                sender_role="faculty",
                receiver_id=103,
                receiver_role="dean",
                comment="Forwarding again.",
            )

    def test_onward_forward_and_return_to_previous_sender(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        # 101 -> 102
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="To HOD",
        )
        # 102 -> 103 (onward forward)
        file_obj.forward(
            sender_id=102,
            sender_role="hod",
            receiver_id=103,
            receiver_role="dean",
            comment="To Dean",
        )
        assert file_obj.current_holder_id == 103
        assert file_obj.get_previous_sender_id() == 102

        # 103 returns to 102 (previous sender)
        ret_m = file_obj.return_file(
            sender_id=103,
            sender_role="dean",
            receiver_id=102,
            receiver_role="hod",
            comment="Please clarify budget lines.",
        )
        assert ret_m.movement_type == MovementType.RETURN
        assert file_obj.current_holder_id == 102
        assert len(file_obj.movements) == 3

    def test_return_to_non_previous_sender_fails(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        # 101 -> 102 -> 103
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="To HOD",
        )
        file_obj.forward(
            sender_id=102,
            sender_role="hod",
            receiver_id=103,
            receiver_role="dean",
            comment="To Dean",
        )
        # Attempt return from 103 directly to 101 instead of 102
        with pytest.raises(InvalidReturnTargetError):
            file_obj.return_file(
                sender_id=103,
                sender_role="dean",
                receiver_id=101,
                receiver_role="faculty",
                comment="Wrong target return",
            )


class TestFileArchival:
    """FTS-UC-007; BR-FTS-012."""

    def test_owner_can_archive_circulated_file(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="For review",
        )
        # Owner (101) archives file
        file_obj.archive(user_id=101)
        assert file_obj.state == FileLifecycleState.ARCHIVED

    def test_non_owner_cannot_archive(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="For review",
        )
        with pytest.raises(ArchivalNotAllowedError):
            file_obj.archive(user_id=102)

    def test_cannot_archive_draft(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        with pytest.raises(ArchivalNotAllowedError):
            file_obj.archive(user_id=101)

    def test_archived_file_cannot_be_forwarded(self):
        file_obj = FileComposite.create_new_draft(
            subject="Proposal",
            description="Desc",
            creator_id=101,
            creator_role="faculty",
            initial_comment="Initial comment",
        )
        file_obj.forward(
            sender_id=101,
            sender_role="faculty",
            receiver_id=102,
            receiver_role="hod",
            comment="For review",
        )
        file_obj.archive(user_id=101)

        with pytest.raises(FileArchivedError):
            file_obj.forward(
                sender_id=102,
                sender_role="hod",
                receiver_id=103,
                receiver_role="dean",
                comment="Cannot forward archived file",
            )

