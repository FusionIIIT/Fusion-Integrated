"""Scoping and visibility tests for FTS (CFR-FTS-006, BR-FTS-009)."""
import pytest

from modules.fts.selectors import scoping
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_inbox_scoping():
    f1 = file_service.create_file(
        subject="File For User 201",
        initial_comment="Review required.",
        creator_id=101,
        receiver_id=201,
    )
    f2 = file_service.create_file(
        subject="File For User 202",
        initial_comment="Review required.",
        creator_id=101,
        receiver_id=202,
    )

    inbox_201 = list(scoping.visible_inbox_files(201))
    assert f1 in inbox_201
    assert f2 not in inbox_201


def test_outbox_scoping():
    f1 = file_service.create_file(
        subject="Sent by 101",
        initial_comment="Submitted.",
        creator_id=101,
        receiver_id=201,
    )

    outbox_101 = list(scoping.visible_outbox_files(101))
    assert f1 in outbox_101

    outbox_201 = list(scoping.visible_outbox_files(201))
    assert f1 not in outbox_201


def test_draft_scoping():
    d1 = file_service.create_file(
        subject="Draft by 101",
        initial_comment="Draft note.",
        creator_id=101,
        is_draft=True,
    )
    d2 = file_service.create_file(
        subject="Draft by 102",
        initial_comment="Draft note.",
        creator_id=102,
        is_draft=True,
    )

    drafts_101 = list(scoping.visible_draft_files(101))
    assert d1 in drafts_101
    assert d2 not in drafts_101


def test_associated_file_access_returns_none_for_strangers():
    f = file_service.create_file(
        subject="Confidential Evaluation",
        initial_comment="Between 101 and 102.",
        creator_id=101,
        receiver_id=102,
    )

    # 101 (creator/owner) and 102 (holder) can see the file
    assert scoping.get_visible_file(f.file_id, 101) is not None
    assert scoping.get_visible_file(f.file_id, 102) is not None

    # 999 (unassociated stranger) cannot see the file
    assert scoping.get_visible_file(f.file_id, 999) is None


def test_get_visible_file_by_pk_and_past_participant():
    f = file_service.create_file(
        subject="Multi-party Inspection",
        initial_comment="Start inspection.",
        creator_id=101,
        receiver_id=102,
    )
    # Forward to 103 so 102 is no longer holder
    file_service.forward_file(
        file_id_or_pk=f.file_id,
        sender_id=102,
        receiver_id=103,
        remarks="Passed to 103.",
    )

    # 102 is past participant in movements: can still see file
    assert scoping.get_visible_file(f.file_id, 102) is not None

    # Querying by numeric PK
    assert scoping.get_visible_file(str(f.id), 101) is not None

    # Non-existent file
    assert scoping.get_visible_file("FTS-2026-NONEXISTENT", 101) is None


def test_scoping_helpers():
    f = file_service.create_file(
        subject="Audit and Helpers Test",
        initial_comment="Initial remark",
        creator_id=101,
        receiver_id=102,
        attachments=[{"file_name": "memo.pdf", "file_path": "/tmp/memo.pdf"}],
    )

    movements = scoping.get_file_movements(f)
    assert movements.count() == 1

    comments = scoping.get_file_comments(f)
    assert comments.count() == 1

    attachments = scoping.get_file_attachments(f)
    assert attachments.count() == 1

    all_logs = scoping.get_system_audit_logs()
    assert all_logs.count() >= 1

    actor_logs = scoping.get_system_audit_logs(actor_id=101)
    assert actor_logs.count() >= 1
