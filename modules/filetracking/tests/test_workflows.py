"""Integration tests for File Tracking System workflows and services."""

import pytest
from django.http import Http404

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.filetracking.domain.entities import FileStatus, MovementAction
from modules.filetracking.models import TrackedFile
from modules.filetracking.selectors import (
    get_associated_file_or_404,
)
from modules.filetracking.services import (
    archive_file,
    create_file,
    discard_draft,
    forward_file,
    return_file,
    update_draft,
)


@pytest.mark.django_db
def test_draft_lifecycle_and_discard():
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Draft Research Proposal",
        initial_comment="Initial draft version 1",
        is_draft=True,
    )
    assert file.status == FileStatus.DRAFT
    assert file.current_holder_user_id is None

    # Update draft
    updated = update_draft(
        file_id=file.id,
        actor_user_id=1,
        actor_designation="faculty",
        subject="Updated Draft Title",
        description="Updated draft notes",
    )
    assert updated.subject == "Updated Draft Title"

    # Discard draft
    discard_draft(file_id=file.id, actor_user_id=1, actor_designation="faculty")
    assert not TrackedFile.objects.filter(id=file.id).exists()


@pytest.mark.django_db
def test_circulation_and_cannot_discard_circulated():
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Lab Equipment Request",
        initial_comment="Need approval for lab budget",
        is_draft=False,
        recipient_user_id=2,
        recipient_designation="Dean Academic",
    )
    assert file.status == FileStatus.CIRCULATING
    assert file.current_holder_user_id == 2

    # Attempting to discard a circulated file must fail (BR-FTS-005)
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=1, actor_designation="faculty")


@pytest.mark.django_db
def test_forward_and_return_workflow():
    # User 1 creates and sends to User 2
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Travel Grant Application",
        initial_comment="Applying for conference travel grant",
        is_draft=False,
        recipient_user_id=2,
        recipient_designation="HOD",
    )
    assert file.current_holder_user_id == 2

    # User 2 forwards to User 3
    mov1 = forward_file(
        file_id=file.id,
        actor_user_id=2,
        actor_designation="HOD",
        recipient_user_id=3,
        recipient_designation="Dean Academic",
        comment="Recommended, forwarding to Dean",
    )
    assert mov1.sequence_number == 2
    file.refresh_from_db()
    assert file.current_holder_user_id == 3

    # User 3 returns to User 2 (immediate previous sender)
    mov2 = return_file(
        file_id=file.id,
        actor_user_id=3,
        actor_designation="Dean Academic",
        comment="Please attach the conference acceptance letter",
    )
    assert mov2.action == MovementAction.RETURNED
    file.refresh_from_db()
    assert file.current_holder_user_id == 2


@pytest.mark.django_db
def test_cannot_self_forward():
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Self Forward Test",
        initial_comment="Testing self forwarding restriction",
        is_draft=False,
        recipient_user_id=2,
        recipient_designation="HOD",
    )
    # User 2 tries to forward to User 2
    with pytest.raises(BadRequestError):
        forward_file(
            file_id=file.id,
            actor_user_id=2,
            actor_designation="HOD",
            recipient_user_id=2,
            recipient_designation="HOD",
            comment="Self forward attempt",
        )


@pytest.mark.django_db
def test_archive_workflow():
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Project Closure",
        initial_comment="Final project submission",
        is_draft=False,
        recipient_user_id=2,
        recipient_designation="Dean",
    )

    # Non-owner attempting to archive must fail (BR-FTS-012)
    with pytest.raises(PermissionDeniedError):
        archive_file(
            file_id=file.id,
            actor_user_id=2,
            actor_designation="Dean",
            comment="Attempting archive",
        )

    # Owner archives
    archived = archive_file(
        file_id=file.id,
        actor_user_id=1,
        actor_designation="faculty",
        comment="Project successfully completed and archived",
    )
    assert archived.is_archived is True
    assert archived.status == FileStatus.ARCHIVED

    # Further forward or return on archived file must fail
    with pytest.raises(ConflictError):
        forward_file(
            file_id=file.id,
            actor_user_id=1,
            actor_designation="faculty",
            recipient_user_id=2,
            recipient_designation="Dean",
            comment="Try forwarding archived file",
        )


@pytest.mark.django_db
def test_scoping_and_visibility():
    file = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Confidential Evaluation",
        initial_comment="Confidential evaluation file",
        is_draft=False,
        recipient_user_id=2,
        recipient_designation="Director",
    )

    # User 1 (creator) and User 2 (holder) can access
    assert get_associated_file_or_404(file.id, user_id=1).id == file.id
    assert get_associated_file_or_404(file.id, user_id=2).id == file.id

    # User 99 (unrelated) gets 404 (BR-FTS-009)
    with pytest.raises(Http404):
        get_associated_file_or_404(file.id, user_id=99)
