"""Service layer tests for FTS (CFR-FTS-001..012, BR-FTS-001..014)."""
import pytest

from core.api.exceptions import ConflictError, PermissionDeniedError
from modules.fts.domain import state_machine as sm
from modules.fts.models import FTSFile
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_create_file_draft():
    file_obj = file_service.create_file(
        subject="Annual Budget Draft",
        description="Budget proposal for Department of CSE",
        initial_comment="Initial draft created for internal review.",
        creator_id=101,
        creator_designation="Assistant Professor",
        is_draft=True,
    )

    assert file_obj.status == sm.DRAFT
    assert file_obj.creator_id == 101
    assert file_obj.owner_id == 101
    assert file_obj.current_holder_id == 101
    assert file_obj.comments.count() == 1
    assert file_obj.movements.count() == 0


def test_create_file_circulating():
    file_obj = file_service.create_file(
        subject="Travel Claim File",
        description="Conference reimbursement claim",
        initial_comment="Please review and approve travel claim.",
        creator_id=101,
        creator_designation="faculty",
        is_draft=False,
        receiver_id=102,
        receiver_designation="Dean Academic",
    )

    assert file_obj.status == sm.CIRCULATING
    assert file_obj.creator_id == 101
    assert file_obj.owner_id == 101
    assert file_obj.current_holder_id == 102
    assert file_obj.movements.count() == 1
    mov = file_obj.movements.first()
    assert mov.sequence_number == 1
    assert mov.sender_id == 101
    assert mov.receiver_id == 102
    assert mov.action == "created"


def test_create_file_with_attachments():
    attachments = [
        {"file_name": "receipt.pdf", "file_path": "/uploads/receipt.pdf", "file_size": 2048},
    ]
    file_obj = file_service.create_file(
        subject="Claim With Bills",
        initial_comment="Attached receipts.",
        creator_id=101,
        is_draft=False,
        receiver_id=102,
        attachments=attachments,
    )
    assert file_obj.attachments.count() == 1
    att = file_obj.attachments.first()
    assert att.uploader_id == 101
    assert att.file_name == "receipt.pdf"


def test_edit_draft():
    file_obj = file_service.create_file(
        subject="Original Title",
        initial_comment="First note.",
        creator_id=101,
        is_draft=True,
    )

    updated = file_service.edit_draft(
        file_id_or_pk=file_obj.file_id,
        user_id=101,
        subject="Updated Title",
        description="New details added.",
        comment="Updated comment.",
    )

    assert updated.subject == "Updated Title"
    assert updated.description == "New details added."
    assert updated.comments.first().comment_text == "Updated comment."


def test_edit_draft_fails_for_non_creator():
    file_obj = file_service.create_file(
        subject="Draft Title",
        initial_comment="Note.",
        creator_id=101,
        is_draft=True,
    )

    with pytest.raises(PermissionDeniedError):
        file_service.edit_draft(
            file_id_or_pk=file_obj.file_id,
            user_id=999,
            subject="Unauthorized Edit",
        )


def test_discard_draft():
    file_obj = file_service.create_file(
        subject="Draft to Discard",
        initial_comment="Disposable note.",
        creator_id=101,
        is_draft=True,
    )

    file_service.discard_draft(file_id_or_pk=file_obj.file_id, user_id=101)
    assert not FTSFile.objects.filter(id=file_obj.id).exists()


def test_forward_file_advances_sequence_and_holder():
    file_obj = file_service.create_file(
        subject="Project Purchase",
        initial_comment="Submitted for review.",
        creator_id=101,
        is_draft=False,
        receiver_id=102,
    )

    mov = file_service.forward_file(
        file_id_or_pk=file_obj.file_id,
        sender_id=102,
        receiver_id=103,
        remarks="Recommended for sanction.",
    )

    file_obj.refresh_from_db()
    assert mov.sequence_number == 2
    assert mov.sender_id == 102
    assert mov.receiver_id == 103
    assert file_obj.current_holder_id == 103
    assert file_obj.status == sm.CIRCULATING


def test_forward_file_refuses_non_holder():
    file_obj = file_service.create_file(
        subject="Procurement File",
        initial_comment="Init.",
        creator_id=101,
        is_draft=False,
        receiver_id=102,
    )

    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(
            file_id_or_pk=file_obj.file_id,
            sender_id=101,
            receiver_id=103,
            remarks="Cannot forward because 101 is not holder.",
        )


def test_return_file_targets_previous_sender():
    file_obj = file_service.create_file(
        subject="Proposal File",
        initial_comment="Sent to HOD.",
        creator_id=101,
        is_draft=False,
        receiver_id=102,
    )

    ret_mov = file_service.return_file(
        file_id_or_pk=file_obj.file_id,
        sender_id=102,
        remarks="Please attach quotation.",
    )

    file_obj.refresh_from_db()
    assert ret_mov.sequence_number == 2
    assert ret_mov.action == "returned"
    assert ret_mov.receiver_id == 101
    assert file_obj.current_holder_id == 101


def test_archive_file_requires_owner():
    file_obj = file_service.create_file(
        subject="Concluded Task",
        initial_comment="Started.",
        creator_id=101,
        is_draft=False,
        receiver_id=102,
    )

    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(
            file_id_or_pk=file_obj.file_id,
            actor_id=102,
            remarks="Non-owner cannot archive.",
        )

    archived = file_service.archive_file(
        file_id_or_pk=file_obj.file_id,
        actor_id=101,
        remarks="Workflow completed.",
    )
    assert archived.status == sm.ARCHIVED

    with pytest.raises(ConflictError):
        file_service.forward_file(
            file_id_or_pk=file_obj.file_id,
            sender_id=101,
            receiver_id=103,
            remarks="Cannot forward archived file.",
        )


def test_service_create_file_validations():
    from core.api.exceptions import BadRequestError

    # Empty subject
    with pytest.raises(BadRequestError) as exc1:
        file_service.create_file(
            subject="",
            initial_comment="Initial remark",
            creator_id=101,
            is_draft=True,
        )
    assert exc1.value.code == "subject_required"

    # Circulating without receiver
    with pytest.raises(BadRequestError) as exc2:
        file_service.create_file(
            subject="Circulating Without Receiver",
            initial_comment="Initial remark",
            creator_id=101,
            is_draft=False,
            receiver_id=None,
        )
    assert exc2.value.code == "recipient_required"

    # With attachments
    f_att = file_service.create_file(
        subject="File with Attachment",
        initial_comment="Initial remark",
        creator_id=101,
        is_draft=True,
        attachments=[{"file_name": "spec.pdf", "file_path": "/tmp/spec.pdf", "file_size": 1024}],
    )
    assert f_att.attachments.count() == 1


def test_service_edit_and_discard_draft_edge_cases():
    from core.api.exceptions import (
        BadRequestError,
        ConflictError,
        NotFoundError,
        PermissionDeniedError,
    )

    f_draft = file_service.create_file(
        subject="Editable Draft",
        initial_comment="Draft note",
        creator_id=101,
        is_draft=True,
    )

    # Edit by non-creator
    with pytest.raises(PermissionDeniedError):
        file_service.edit_draft(
            file_id_or_pk=f_draft.file_id,
            user_id=102,
            subject="Unauthorized Edit",
        )

    # Edit with empty subject
    with pytest.raises(BadRequestError):
        file_service.edit_draft(
            file_id_or_pk=f_draft.file_id,
            user_id=101,
            subject="   ",
        )

    # Edit not found
    with pytest.raises(NotFoundError):
        file_service.edit_draft(
            file_id_or_pk="FTS-2026-NONEXISTENT",
            user_id=101,
            subject="Missing",
        )

    # Discard by non-creator
    with pytest.raises(PermissionDeniedError):
        file_service.discard_draft(
            file_id_or_pk=f_draft.file_id,
            user_id=102,
        )

    # Discard not found
    with pytest.raises(NotFoundError):
        file_service.discard_draft(
            file_id_or_pk="FTS-2026-NONEXISTENT",
            user_id=101,
        )

    # Discard non-draft
    f_circ = file_service.create_file(
        subject="Circulating File",
        initial_comment="Note",
        creator_id=101,
        receiver_id=102,
        is_draft=False,
    )
    with pytest.raises(ConflictError):
        file_service.discard_draft(
            file_id_or_pk=f_circ.file_id,
            user_id=101,
        )
    with pytest.raises(ConflictError):
        file_service.edit_draft(
            file_id_or_pk=f_circ.file_id,
            user_id=101,
            subject="Try to edit circulating",
        )


def test_service_forward_and_return_edge_cases():
    from core.api.exceptions import NotFoundError

    # Forward not found
    with pytest.raises(NotFoundError):
        file_service.forward_file(
            file_id_or_pk="FTS-2026-NONEXISTENT",
            sender_id=101,
            receiver_id=102,
            remarks="Forward missing",
        )

    # Return not found
    with pytest.raises(NotFoundError):
        file_service.return_file(
            file_id_or_pk="FTS-2026-NONEXISTENT",
            sender_id=102,
            remarks="Return missing",
        )

    # Forward draft before submission
    f_draft = file_service.create_file(
        subject="Uncirculated Draft",
        initial_comment="Draft note",
        creator_id=101,
        is_draft=True,
    )
    # Forwarding draft circulates it with attachment
    fwd_mov = file_service.forward_file(
        file_id_or_pk=f_draft.file_id,
        sender_id=101,
        receiver_id=102,
        remarks="Circulating draft",
        attachments=[{"file_name": "memo.pdf", "file_path": "/tmp/memo.pdf"}],
    )
    assert fwd_mov.sequence_number == 1
    assert fwd_mov.file.status == sm.CIRCULATING


def test_service_archive_edge_cases():
    from core.api.exceptions import ConflictError, NotFoundError

    with pytest.raises(NotFoundError):
        file_service.archive_file(
            file_id_or_pk="FTS-2026-NONEXISTENT",
            actor_id=101,
            remarks="Archive missing",
        )

    f_draft = file_service.create_file(
        subject="Draft Archival Attempt",
        initial_comment="Draft note",
        creator_id=101,
        is_draft=True,
    )
    with pytest.raises(ConflictError):
        file_service.archive_file(
            file_id_or_pk=f_draft.file_id,
            actor_id=101,
            remarks="Cannot archive draft",
        )
