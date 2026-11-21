"""Tests for FTS service functions."""
import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)
from modules.fts.models.audit import FileAuditLog, NotificationEvent
from modules.fts.services.archival import archive_file
from modules.fts.services.audit import verify_all_files_audit_integrity
from modules.fts.services.files import create_file, discard_draft, update_draft
from modules.fts.services.movements import forward_file, return_file

pytestmark = pytest.mark.django_db


def test_create_file_as_draft():
    file_obj = create_file(
        subject="Lab Equipment Requisition",
        description="Requisition of components.",
        comment_text="Initial draft for committee review.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        actor_kind="faculty",
        is_draft=True,
    )
    assert file_obj.status == STATE_DRAFT
    assert file_obj.current_holder_user_id == 101
    assert file_obj.movements.count() == 1
    assert file_obj.comments.count() == 1
    assert FileAuditLog.objects.filter(file_id=file_obj.id, action="FILE_CREATED").exists()


def test_create_file_immediate_circulate():
    file_obj = create_file(
        subject="PhD Thesis Submission",
        description="Submission of final thesis draft.",
        comment_text="Submitted to Dean Academic for evaluation.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        actor_kind="faculty",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="dean_acad",
        recipient_role="Dean Academic",
    )
    assert file_obj.status == STATE_CIRCULATED
    assert file_obj.current_holder_user_id == 202
    assert NotificationEvent.objects.filter(event_type="FILE_RECEIVED", recipient_user_id=202).exists()


def test_update_draft():
    file_obj = create_file(
        subject="Old Subject",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    updated = update_draft(
        file_id=file_obj.id,
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        subject="New Subject",
        comment_text="Updated comment text.",
    )
    assert updated.subject == "New Subject"
    assert updated.comments.first().comment_text == "Updated comment text."


def test_discard_draft():
    file_obj = create_file(
        subject="Draft to discard",
        comment_text="Initial draft.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    discarded = discard_draft(
        file_id=file_obj.id,
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
    )
    assert discarded.status == STATE_DISCARDED


def test_cannot_discard_circulated_file():
    file_obj = create_file(
        subject="Circulated file",
        comment_text="Submitted directly.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=202,
        recipient_username="dean_acad",
        recipient_role="Dean Academic",
    )
    with pytest.raises(ConflictError):
        discard_draft(
            file_id=file_obj.id,
            actor_user_id=101,
            actor_username="faculty_1",
            actor_role="Assistant Professor",
        )


def test_forward_and_return_cycle():
    file_obj = create_file(
        subject="Syllabus Revision",
        comment_text="Submitted to HoD.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="hod_cse",
        recipient_role="HOD (CSE)",
    )

    # HoD forwards to Dean
    mov2 = forward_file(
        file_id=file_obj.id,
        actor_user_id=201,
        actor_username="hod_cse",
        actor_role="HOD (CSE)",
        actor_kind="faculty",
        to_user_id=301,
        to_username="dean_acad",
        to_role="Dean Academic",
        comment_text="Recommended for approval.",
    )
    assert mov2.sequence == 2
    file_obj.refresh_from_db()
    assert file_obj.current_holder_user_id == 301

    # Dean returns to HoD
    mov3 = return_file(
        file_id=file_obj.id,
        actor_user_id=301,
        actor_username="dean_acad",
        actor_role="Dean Academic",
        actor_kind="faculty",
        comment_text="Please attach meeting minutes before sanction.",
    )
    assert mov3.sequence == 3
    file_obj.refresh_from_db()
    assert file_obj.current_holder_user_id == 201

    # Integrity verification
    assert verify_all_files_audit_integrity() is True


def test_archive_file():
    file_obj = create_file(
        subject="Project Closeout",
        comment_text="Initiating project.",
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="staff_admin",
        recipient_role="Junior Superintendent",
    )

    # Non-owner cannot archive
    with pytest.raises(PermissionDeniedError):
        archive_file(
            file_id=file_obj.id,
            actor_user_id=201,
            actor_username="staff_admin",
            actor_role="Junior Superintendent",
        )

    # Owner archives
    archived = archive_file(
        file_id=file_obj.id,
        actor_user_id=101,
        actor_username="faculty_1",
        actor_role="Assistant Professor",
    )
    assert archived.status == STATE_ARCHIVED
    assert archived.archived_at is not None

    # Archived file cannot be forwarded
    with pytest.raises(ConflictError):
        forward_file(
            file_id=file_obj.id,
            actor_user_id=101,
            actor_username="faculty_1",
            actor_role="Assistant Professor",
            to_user_id=201,
            to_username="staff_admin",
            to_role="Junior Superintendent",
            comment_text="Try to forward archived file.",
        )
