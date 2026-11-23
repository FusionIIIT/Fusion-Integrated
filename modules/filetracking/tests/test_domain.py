"""Unit tests for pure domain rules and state machine (framework-free)."""

import pytest

from modules.filetracking.domain.entities import FileEvent, FileStatus
from modules.filetracking.domain.errors import (
    CommentRequiredError,
    DraftDiscardError,
    FileArchivedError,
    InvalidAttachmentError,
    InvalidRecipientError,
    StateTransitionError,
)
from modules.filetracking.domain.rules import (
    validate_attachment,
    validate_draft_for_discard,
    validate_file_not_archived,
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_owner_for_archive,
    validate_return_recipient,
)
from modules.filetracking.domain.state_machine import can_transition, get_next_state


def test_initial_comment_validation():
    validate_initial_comment("Valid initial comment")
    with pytest.raises(CommentRequiredError):
        validate_initial_comment("")
    with pytest.raises(CommentRequiredError):
        validate_initial_comment("   ")
    with pytest.raises(CommentRequiredError):
        validate_initial_comment(None)


def test_movement_comment_validation():
    validate_movement_comment("Forwarding note")
    with pytest.raises(CommentRequiredError):
        validate_movement_comment("")
    with pytest.raises(CommentRequiredError):
        validate_movement_comment("   ")
    with pytest.raises(CommentRequiredError):
        validate_movement_comment(None)


def test_forward_recipient_validation():
    validate_forward_recipient(sender_user_id=1, recipient_user_id=2)
    with pytest.raises(InvalidRecipientError):
        validate_forward_recipient(sender_user_id=1, recipient_user_id=1)


def test_return_recipient_validation():
    validate_return_recipient(expected_sender_id=2, target_recipient_id=2)
    with pytest.raises(InvalidRecipientError):
        validate_return_recipient(expected_sender_id=2, target_recipient_id=3)


def test_draft_for_discard_validation():
    validate_draft_for_discard(FileStatus.DRAFT)
    with pytest.raises(DraftDiscardError):
        validate_draft_for_discard(FileStatus.CIRCULATING)
    with pytest.raises(DraftDiscardError):
        validate_draft_for_discard(FileStatus.ARCHIVED)


def test_file_not_archived_validation():
    validate_file_not_archived(FileStatus.DRAFT)
    validate_file_not_archived(FileStatus.CIRCULATING)
    with pytest.raises(FileArchivedError):
        validate_file_not_archived(FileStatus.ARCHIVED)


def test_owner_for_archive_validation():
    validate_owner_for_archive(owner_user_id=10, actor_user_id=10)
    with pytest.raises(StateTransitionError):
        validate_owner_for_archive(owner_user_id=10, actor_user_id=20)


def test_attachment_validation():
    validate_attachment("doc.pdf", 1024, "application/pdf")
    with pytest.raises(InvalidAttachmentError):
        validate_attachment("empty.pdf", 0, "application/pdf")
    with pytest.raises(InvalidAttachmentError):
        validate_attachment("huge.pdf", 10 * 1024 * 1024 + 1, "application/pdf")
    with pytest.raises(InvalidAttachmentError):
        validate_attachment("bad.exe", 1024, "application/x-msdownload")


def test_state_machine_draft_transitions():
    assert can_transition(FileStatus.DRAFT, FileEvent.UPDATE_DRAFT, "OWNER")
    assert can_transition(FileStatus.DRAFT, FileEvent.DISCARD_DRAFT, "OWNER")
    assert can_transition(FileStatus.DRAFT, FileEvent.SUBMIT_INITIAL, "OWNER")

    assert get_next_state(FileStatus.DRAFT, FileEvent.UPDATE_DRAFT, "OWNER") == FileStatus.DRAFT
    assert get_next_state(FileStatus.DRAFT, FileEvent.DISCARD_DRAFT, "OWNER") is None
    assert (
        get_next_state(FileStatus.DRAFT, FileEvent.SUBMIT_INITIAL, "OWNER")
        == FileStatus.CIRCULATING
    )

    with pytest.raises(StateTransitionError):
        get_next_state(FileStatus.DRAFT, FileEvent.SUBMIT_INITIAL, "OTHER")


def test_state_machine_circulating_transitions():
    assert can_transition(FileStatus.CIRCULATING, FileEvent.FORWARD, "CURRENT_HOLDER")
    assert can_transition(FileStatus.CIRCULATING, FileEvent.RETURN, "CURRENT_HOLDER")
    assert can_transition(FileStatus.CIRCULATING, FileEvent.ARCHIVE, "OWNER")

    assert (
        get_next_state(FileStatus.CIRCULATING, FileEvent.FORWARD, "CURRENT_HOLDER")
        == FileStatus.CIRCULATING
    )
    assert (
        get_next_state(FileStatus.CIRCULATING, FileEvent.RETURN, "CURRENT_HOLDER")
        == FileStatus.CIRCULATING
    )
    assert get_next_state(FileStatus.CIRCULATING, FileEvent.ARCHIVE, "OWNER") == FileStatus.ARCHIVED


def test_state_machine_illegal_transitions():
    with pytest.raises(DraftDiscardError):
        get_next_state(FileStatus.CIRCULATING, FileEvent.DISCARD_DRAFT, "OWNER")

    with pytest.raises(FileArchivedError):
        get_next_state(FileStatus.ARCHIVED, FileEvent.FORWARD, "CURRENT_HOLDER")

    assert not can_transition(FileStatus.DRAFT, "NONEXISTENT_EVENT", "OWNER")
    assert not can_transition(FileStatus.DRAFT, FileEvent.UPDATE_DRAFT, "NON_OWNER")

    with pytest.raises(StateTransitionError) as exc:
        get_next_state(FileStatus.DRAFT, "NONEXISTENT_EVENT", "OWNER")
    assert "illegal" in str(exc.value)


def test_domain_error_instantiations():
    from modules.filetracking.domain.errors import (
        AuthorizationError,
        ResourceNotFoundError,
    )

    err1 = AuthorizationError("Permission denied.")
    assert err1.code == "unauthorized_action"

    err2 = ResourceNotFoundError("File not found.")
    assert err2.code == "resource_not_found"


def test_registry_readiness():
    from modules.filetracking.registry import readiness

    assert readiness() == []


@pytest.mark.django_db
def test_model_string_representations():
    from modules.filetracking.models import (
        FileAttachment,
        FileAuditLog,
        FileMovement,
        FileStatus,
        MovementAction,
        TrackedFile,
    )

    file = TrackedFile.objects.create(
        file_number="FTS-STR-01",
        subject="String Test File",
        status=FileStatus.DRAFT,
        created_by_user_id=1,
    )
    assert "FTS-STR-01" in str(file)

    mov = FileMovement.objects.create(
        file=file,
        sequence_number=1,
        action=MovementAction.CREATED,
        sender_user_id=1,
        receiver_user_id=2,
        comment="Test mov",
    )
    assert "Movement #1" in str(mov)

    att = FileAttachment.objects.create(
        file=file,
        movement=mov,
        uploaded_by_user_id=1,
        uploader_designation="faculty",
        file_name="sample.pdf",
        file_path="test/sample.pdf",
        file_size=1024,
        mime_type="application/pdf",
    )
    assert "sample.pdf" in str(att)

    audit = FileAuditLog.objects.create(
        file_id=file.id,
        actor_user_id=1,
        actor_designation="faculty",
        action="TEST_ACTION",
    )
    assert "TEST_ACTION" in str(audit)
