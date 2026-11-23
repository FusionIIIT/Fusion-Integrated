"""Specification-based tests for File Tracking System workflows (WF Strategy).

Derived strictly from 05_FTS_Workflow_Specifications_v1.3_FINAL.docx and WF_DESIGN.json.
"""

import pytest

from core.api.exceptions import ConflictError
from modules.filetracking.domain.entities import FileStatus, MovementAction
from modules.filetracking.models import TrackedFile
from modules.filetracking.services import (
    archive_file,
    create_file,
    discard_draft,
    forward_file,
    return_file,
    update_draft,
)

pytestmark = pytest.mark.django_db


def test_wf_001_bw_fts_01():
    """TEST-WF-001 | BW-FTS-01 canonical-path: Forward File to Recipient — Zero Onward Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Project Proposal A",
        initial_comment="Draft review",
        is_draft=True,
    )
    m = forward_file(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        recipient_user_id=102,
        recipient_designation="Dean Academic",
        comment="Please review",
    )
    assert m.action == MovementAction.FORWARDED
    file.refresh_from_db()
    assert file.status == FileStatus.CIRCULATING
    assert file.current_holder_user_id == 102


def test_wf_002_bw_fts_02():
    """TEST-WF-002 | BW-FTS-02 canonical-path: Onward Forwarding — One Loop Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Multi-hop Proposal",
        initial_comment="Initial creation",
        is_draft=False,
        recipient_user_id=102,
        recipient_designation="Dean Academic",
    )
    # Recipient 102 forwards onward to 103
    m = forward_file(
        file_id=file.id,
        actor_user_id=102,
        actor_designation="Dean Academic",
        recipient_user_id=103,
        recipient_designation="Director",
        comment="Forwarding for final review",
    )
    assert m.receiver_user_id == 103
    file.refresh_from_db()
    assert file.current_holder_user_id == 103
    assert file.movements.count() == 2


def test_wf_003_bw_fts_03():
    """TEST-WF-003 | BW-FTS-03 canonical-path: Return File to Previous Sender."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Budget Review Memo",
        initial_comment="Please inspect budget",
        is_draft=False,
        recipient_user_id=102,
        recipient_designation="Registrar",
    )
    # Recipient returns to sender 101
    m = return_file(
        file_id=file.id,
        actor_user_id=102,
        actor_designation="Registrar",
        comment="Needs revision in itemized figures",
    )
    assert m.action == MovementAction.RETURNED
    assert m.receiver_user_id == 101
    file.refresh_from_db()
    assert file.current_holder_user_id == 101
    assert file.movements.count() == 2


def test_wf_004_bw_fts_04():
    """TEST-WF-004 | BW-FTS-04 canonical-path: Archive Completed Circulated File."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Completed Committee Resolution",
        initial_comment="Signed resolution",
        is_draft=False,
        recipient_user_id=102,
        recipient_designation="Director",
    )
    return_file(
        file_id=file.id,
        actor_user_id=102,
        actor_designation="Director",
        comment="Approved and returned to owner",
    )
    archived = archive_file(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
    )
    assert archived.status == FileStatus.ARCHIVED
    assert archived.current_holder_user_id is None


def test_wf_005_bw_fts_05():
    """TEST-WF-005 | BW-FTS-05 canonical-path: Prepare and Circulate New File — Zero Draft-Edit Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Immediate Circulation File",
        initial_comment="Direct circulate without draft saving",
        is_draft=False,
        recipient_user_id=102,
        recipient_designation="Head of Department",
    )
    assert file.status == FileStatus.CIRCULATING
    assert file.current_holder_user_id == 102


def test_wf_006_bw_fts_06():
    """TEST-WF-006 | BW-FTS-06 canonical-path: Prepare and Circulate New File — One Draft-Edit Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Draft With One Edit",
        initial_comment="Draft v1",
        is_draft=True,
    )
    assert file.status == FileStatus.DRAFT
    # Edit once
    update_draft(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        subject="Draft With One Edit (Revised)",
    )
    # Forward/Circulate
    m = forward_file(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        recipient_user_id=102,
        recipient_designation="Dean Academic",
        comment="Sending edited draft for circulation",
    )
    assert m.receiver_user_id == 102
    file.refresh_from_db()
    assert file.status == FileStatus.CIRCULATING


def test_wf_007_bw_fts_07():
    """TEST-WF-007 | BW-FTS-07 canonical-path: Create and Discard Draft — Zero Draft-Edit Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Abandoned Draft File",
        initial_comment="Initial draft text",
        is_draft=True,
    )
    assert TrackedFile.objects.filter(id=file.id).exists()
    discard_draft(file_id=file.id, actor_user_id=101, actor_designation="faculty")
    assert not TrackedFile.objects.filter(id=file.id).exists()


def test_wf_008_bw_fts_08():
    """TEST-WF-008 | BW-FTS-08 canonical-path: Edit Once and Discard Draft — One Draft-Edit Traversal."""
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Draft To Edit Then Discard",
        initial_comment="Initial draft",
        is_draft=True,
    )
    update_draft(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        subject="Draft To Edit Then Discard - Edited",
    )
    discard_draft(file_id=file.id, actor_user_id=101, actor_designation="faculty")
    assert not TrackedFile.objects.filter(id=file.id).exists()


def test_wf_009_cw_fts_01():
    """TEST-WF-009 | CW-FTS-01 canonical-path: Collaborative File Circulation and Completion."""
    # 1. Create and circulate
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Collaborative Policy Doc",
        initial_comment="Policy review kickoff",
        is_draft=False,
        recipient_user_id=102,
        recipient_designation="Committee Chair",
    )
    # 2. Onward forward to 103
    forward_file(
        file_id=file.id,
        actor_user_id=102,
        actor_designation="Committee Chair",
        recipient_user_id=103,
        recipient_designation="Legal Counsel",
        comment="Please check legal clauses",
    )
    # 3. Return to 102
    return_file(
        file_id=file.id,
        actor_user_id=103,
        actor_designation="Legal Counsel",
        comment="Legal clauses verified and approved",
    )
    # 4. Return to owner 101
    return_file(
        file_id=file.id,
        actor_user_id=102,
        actor_designation="Committee Chair",
        comment="Committee concluded review, returning to creator",
    )
    # 5. Archive by owner
    archived = archive_file(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
    )
    assert archived.status == FileStatus.ARCHIVED


def test_wf_010_cw_fts_02():
    """TEST-WF-010 | CW-FTS-02 canonical-path: New File Preparation and Initial Outcome."""
    # Lifecycle: create draft, update draft, circulate, verify circulating state cannot be discarded
    file = create_file(
        creator_user_id=101,
        creator_designation="faculty",
        subject="Curriculum Update Proposal",
        initial_comment="Rough syllabus draft",
        is_draft=True,
    )
    update_draft(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        subject="Curriculum Update Proposal Finalized",
    )
    forward_file(
        file_id=file.id,
        actor_user_id=101,
        actor_designation="faculty",
        recipient_user_id=102,
        recipient_designation="Dean Academic",
        comment="Submitting finalized proposal",
    )
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=101, actor_designation="faculty")
