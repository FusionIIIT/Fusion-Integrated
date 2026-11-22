"""Tests for FTS service functions."""
import pytest

from core.api.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from modules.fts.domain.state_machine import (
    STATE_ARCHIVED,
    STATE_CIRCULATED,
    STATE_DISCARDED,
    STATE_DRAFT,
)
from modules.fts.models.audit import FileAuditLog, NotificationEvent
from modules.fts.selectors.scoping import get_file_for_user
from modules.fts.services.archival import archive_file
from modules.fts.services.audit import verify_all_files_audit_integrity
from modules.fts.services.files import create_file, discard_draft, update_draft
from modules.fts.services.movements import forward_file, return_file

pytestmark = pytest.mark.django_db


def test_create_file_as_draft():
    """BR-FTS-003, BR-FTS-004, BR-FTS-005, FTS-UC-001, BW-FTS-01: Create file draft."""
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
    """BR-FTS-001, BR-FTS-003, BR-FTS-004, BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-013, FTS-UC-003, BW-FTS-02: Create and circulate file."""
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
    """BR-FTS-005, FTS-UC-002: Update draft file metadata and comment."""
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
    """BR-FTS-005, FTS-UC-002, BW-FTS-07: Discard unsubmitted draft."""
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
    """BR-FTS-003, BR-FTS-005, BW-FTS-07: Circulated files cannot be discarded."""
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
    """BR-FTS-006, BR-FTS-007, BR-FTS-008, BR-FTS-011, FTS-UC-004, FTS-UC-005, BW-FTS-03, BW-FTS-04: Forward and return cycles."""
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
    """BR-FTS-010, BR-FTS-012, FTS-UC-006, BW-FTS-05: Archival of completed file."""
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


def test_role_switching_preservation_rule():
    """BR-FTS-002: Switching role context preserves file ownership and historical audit identity."""
    # Faculty creates file while acting as Assistant Professor
    file_obj = create_file(
        subject="Research Grant Proposal",
        comment_text="Submitted under department context.",
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="hod_ece",
        recipient_role="HOD (ECE)",
    )
    initial_mov = file_obj.movements.order_by("sequence").first()
    assert initial_mov.from_role == "Assistant Professor"
    assert file_obj.owner_user_id == 101

    # Later, HoD forwards back to user 101
    forward_file(
        file_id=file_obj.id,
        actor_user_id=201,
        actor_username="hod_ece",
        actor_role="HOD (ECE)",
        to_user_id=101,
        to_username="prof_101",
        to_role="Dean R&D",
        comment_text="Please sign as Dean R&D.",
    )

    # User 101 switches role context to Dean R&D and forwards to Director
    sec_mov = forward_file(
        file_id=file_obj.id,
        actor_user_id=101,
        actor_username="prof_101",
        actor_role="Dean R&D",
        to_user_id=301,
        to_username="director",
        to_role="Director",
        comment_text="Endorsed from Dean office.",
    )
    assert sec_mov.from_role == "Dean R&D"

    # Historical record remains untouched and ownership is preserved
    initial_mov.refresh_from_db()
    assert initial_mov.from_role == "Assistant Professor"
    file_obj.refresh_from_db()
    assert file_obj.owner_user_id == 101


def test_forward_and_return_edge_cases():
    """Additional branch coverage for forward and return validations and attachments."""
    file_obj = create_file(
        subject="Attachment Test File",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="faculty_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="staff_201",
        recipient_role="Assistant",
    )

    # Forward with attachments
    mov = forward_file(
        file_id=file_obj.id,
        actor_user_id=201,
        actor_username="staff_201",
        actor_role="Assistant",
        to_user_id=301,
        to_username="super_301",
        to_role="Superintendent",
        comment_text="Forwarding with attachment.",
        attachments=[
            {
                "file_name": "evidence.pdf",
                "file_url": "https://storage.fusion.ac.in/fts/evidence.pdf",
                "file_size": 1024,
                "mime_type": "application/pdf",
            }
        ],
    )
    assert mov.attachments.count() == 1

    # Non-holder cannot forward
    with pytest.raises(PermissionDeniedError):
        forward_file(
            file_id=file_obj.id,
            actor_user_id=201,
            actor_username="staff_201",
            actor_role="Assistant",
            to_user_id=401,
            to_username="admin_401",
            to_role="Admin",
            comment_text="Attempting illegal forward.",
        )

    # Non-existent file cannot be forwarded
    with pytest.raises(NotFoundError):
        forward_file(
            file_id=999999,
            actor_user_id=301,
            actor_username="super_301",
            actor_role="Superintendent",
            to_user_id=401,
            to_username="admin_401",
            to_role="Admin",
            comment_text="Non existent file forward.",
        )

    # Return with attachment
    ret_mov = return_file(
        file_id=file_obj.id,
        actor_user_id=301,
        actor_username="super_301",
        actor_role="Superintendent",
        comment_text="Returning with review memo.",
        attachments=[
            {
                "file_name": "memo.pdf",
                "file_url": "https://storage.fusion.ac.in/fts/memo.pdf",
                "file_size": 512,
                "mime_type": "application/pdf",
            }
        ],
    )
    assert ret_mov.attachments.count() == 1

    # Non-existent file return
    with pytest.raises(NotFoundError):
        return_file(
            file_id=999999,
            actor_user_id=201,
            actor_username="staff_201",
            actor_role="Assistant",
            comment_text="Non existent file return.",
        )


def test_archival_edge_cases():
    """Branch coverage for archival failure modes."""
    # Draft file cannot be archived
    draft = create_file(
        subject="Draft Archival Test",
        comment_text="Draft comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=True,
    )
    with pytest.raises(ConflictError):
        archive_file(
            file_id=draft.id,
            actor_user_id=101,
            actor_username="fac_101",
            actor_role="Assistant Professor",
        )

    # Non-existent file archival
    with pytest.raises(NotFoundError):
        archive_file(
            file_id=999999,
            actor_user_id=101,
            actor_username="fac_101",
            actor_role="Assistant Professor",
        )

    # Admin actor cannot archive
    circ = create_file(
        subject="Circulated Archival Test",
        comment_text="Circ comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="staff_201",
        recipient_role="Assistant",
    )
    with pytest.raises(PermissionDeniedError):
        archive_file(
            file_id=circ.id,
            actor_user_id=101,
            actor_username="fac_101",
            actor_role="Assistant Professor",
            is_admin_actor=True,
        )


def test_scoping_helpers():
    """Branch coverage for scoping selector functions."""
    file_obj = create_file(
        subject="Scoping Helper Test",
        comment_text="Initial comment.",
        actor_user_id=101,
        actor_username="fac_101",
        actor_role="Assistant Professor",
        is_draft=False,
        recipient_user_id=201,
        recipient_username="staff_201",
        recipient_role="Assistant",
    )

    # Admin can retrieve any file
    assert get_file_for_user(file_obj.id, 999, is_admin=True).id == file_obj.id

    # Non-existent file raises NotFoundError
    with pytest.raises(NotFoundError):
        get_file_for_user(999999, 101)

    # Non-associated user raises NotFoundError
    with pytest.raises(NotFoundError):
        get_file_for_user(file_obj.id, 555)
