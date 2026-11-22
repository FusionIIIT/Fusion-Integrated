"""Unit and integration tests for filetracking service functions and refusals."""

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from modules.filetracking.models import (
    FileStatus,
    TrackedFile,
)
from modules.filetracking.services import (
    archive_file,
    create_file,
    discard_draft,
    forward_file,
    return_file,
    update_draft,
)

pytestmark = pytest.mark.django_db


def test_create_file_validation_errors():
    with pytest.raises(BadRequestError) as exc:
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="",
            initial_comment="valid comment",
            is_draft=True,
        )
    assert exc.value.code == "subject_required"

    with pytest.raises(BadRequestError) as exc:
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Subj",
            initial_comment="",
            is_draft=True,
        )
    assert exc.value.code == "comment_required"

    with pytest.raises(BadRequestError) as exc:
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Subj",
            initial_comment="Comment",
            is_draft=False,
            recipient_user_id=None,
        )
    assert exc.value.code == "recipient_required"

    with pytest.raises(BadRequestError) as exc:
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Subj",
            initial_comment="Comment",
            is_draft=False,
            recipient_user_id=1,
        )
    assert exc.value.code == "invalid_recipient"

    with pytest.raises(BadRequestError) as exc:
        create_file(
            creator_user_id=1,
            creator_designation="faculty",
            subject="Subj",
            initial_comment="Comment",
            is_draft=True,
            attachments=[{"file_name": "bad.exe", "file_size": 100, "mime_type": "app/exe"}],
        )
    assert exc.value.code == "invalid_attachment"


def test_update_draft_errors_and_success():
    draft = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Draft 1",
        initial_comment="Initial",
        is_draft=True,
    )

    with pytest.raises(NotFoundError):
        update_draft(
            file_id=9999,
            actor_user_id=1,
            actor_designation="faculty",
            subject="New",
        )

    with pytest.raises(PermissionDeniedError):
        update_draft(
            file_id=draft.id,
            actor_user_id=2,
            actor_designation="faculty",
            subject="New",
        )

    # Circulate another file and try to update it as draft
    circ = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Circ 1",
        initial_comment="Initial",
        is_draft=False,
        recipient_user_id=2,
    )
    with pytest.raises(ConflictError):
        update_draft(
            file_id=circ.id,
            actor_user_id=1,
            actor_designation="faculty",
            subject="New",
        )

    # Successful update
    updated = update_draft(
        file_id=draft.id,
        actor_user_id=1,
        actor_designation="faculty",
        subject="Updated Subject",
        description="Updated Note",
        attachments=[{"file_name": "valid.pdf", "file_size": 500, "mime_type": "application/pdf"}],
    )
    assert updated.subject == "Updated Subject"
    assert updated.description == "Updated Note"
    assert updated.attachments.count() == 1


def test_discard_draft_errors():
    draft = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Draft to discard",
        initial_comment="Note",
        is_draft=True,
    )

    with pytest.raises(NotFoundError):
        discard_draft(file_id=9999, actor_user_id=1, actor_designation="faculty")

    with pytest.raises(PermissionDeniedError):
        discard_draft(file_id=draft.id, actor_user_id=2, actor_designation="faculty")

    circ = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Circ file",
        initial_comment="Note",
        is_draft=False,
        recipient_user_id=2,
    )
    with pytest.raises(ConflictError):
        discard_draft(file_id=circ.id, actor_user_id=1, actor_designation="faculty")


def test_forward_file_errors():
    circ = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="File to forward",
        initial_comment="Note",
        is_draft=False,
        recipient_user_id=2,
    )

    with pytest.raises(NotFoundError):
        forward_file(
            file_id=9999,
            actor_user_id=2,
            actor_designation="faculty",
            recipient_user_id=3,
            recipient_designation="staff",
            comment="Comment",
        )

    # User 1 is not the current holder (User 2 is)
    with pytest.raises(PermissionDeniedError):
        forward_file(
            file_id=circ.id,
            actor_user_id=1,
            actor_designation="faculty",
            recipient_user_id=3,
            recipient_designation="staff",
            comment="Comment",
        )

    # Recipient cannot be self
    with pytest.raises(BadRequestError):
        forward_file(
            file_id=circ.id,
            actor_user_id=2,
            actor_designation="faculty",
            recipient_user_id=2,
            recipient_designation="faculty",
            comment="Comment",
        )

    # Comment cannot be empty
    with pytest.raises(BadRequestError):
        forward_file(
            file_id=circ.id,
            actor_user_id=2,
            actor_designation="faculty",
            recipient_user_id=3,
            recipient_designation="staff",
            comment="",
        )

    # Invalid attachment
    with pytest.raises(BadRequestError):
        forward_file(
            file_id=circ.id,
            actor_user_id=2,
            actor_designation="faculty",
            recipient_user_id=3,
            recipient_designation="staff",
            comment="Comment",
            attachments=[{"file_name": "bad.bin", "file_size": 0, "mime_type": "application/pdf"}],
        )


def test_return_file_errors():
    circ = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="File to return",
        initial_comment="Note",
        is_draft=False,
        recipient_user_id=2,
    )

    with pytest.raises(NotFoundError):
        return_file(
            file_id=9999,
            actor_user_id=2,
            actor_designation="faculty",
            comment="Comment",
        )

    # User 1 is not holder
    with pytest.raises(PermissionDeniedError):
        return_file(
            file_id=circ.id,
            actor_user_id=1,
            actor_designation="faculty",
            comment="Comment",
        )

    # Empty comment
    with pytest.raises(BadRequestError):
        return_file(
            file_id=circ.id,
            actor_user_id=2,
            actor_designation="faculty",
            comment="",
        )

    # File with no previous movement
    orphan = TrackedFile.objects.create(
        file_number="FTS-ORPHAN-01",
        subject="Orphan",
        status=FileStatus.CIRCULATING,
        created_by_user_id=1,
        current_holder_user_id=2,
    )
    with pytest.raises(ConflictError):
        return_file(
            file_id=orphan.id,
            actor_user_id=2,
            actor_designation="faculty",
            comment="Returning orphan",
        )


def test_archive_file_errors():
    circ = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="File to archive",
        initial_comment="Note",
        is_draft=False,
        recipient_user_id=2,
    )

    with pytest.raises(NotFoundError):
        archive_file(
            file_id=9999,
            actor_user_id=1,
            actor_designation="faculty",
            comment="Done",
        )

    # Non-creator/owner cannot archive
    with pytest.raises(PermissionDeniedError):
        archive_file(
            file_id=circ.id,
            actor_user_id=2,
            actor_designation="faculty",
            comment="Done",
        )

    # Draft cannot be archived
    draft = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Draft file",
        initial_comment="Note",
        is_draft=True,
    )
    with pytest.raises(ConflictError):
        archive_file(
            file_id=draft.id,
            actor_user_id=1,
            actor_designation="faculty",
            comment="Done",
        )

    # Successfully archive circ
    archived = archive_file(
        file_id=circ.id,
        actor_user_id=1,
        actor_designation="faculty",
        comment="Archived successfully",
    )
    assert archived.status == FileStatus.ARCHIVED
    assert archived.is_archived is True

    # Re-archiving an archived file
    with pytest.raises(ConflictError):
        archive_file(
            file_id=circ.id,
            actor_user_id=1,
            actor_designation="faculty",
            comment="Archiving again",
        )
