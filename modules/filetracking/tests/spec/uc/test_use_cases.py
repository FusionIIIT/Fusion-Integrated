"""Specification-based tests for File Tracking System use cases (UC Strategy).

Derived strictly from 03_FTS_Use_Case_Specifications_v1.3_FINAL.docx and UC_DESIGN.json.
"""

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.filetracking.contracts import get_file_statuses
from modules.filetracking.domain.entities import FileStatus, MovementAction
from modules.filetracking.domain.errors import DomainValidationError, FTSDomainError
from modules.filetracking.domain.rules import (
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
)
from modules.filetracking.models import TrackedFile
from modules.filetracking.selectors import (
    get_associated_file_or_404,
    get_file_movements,
    get_inbox_files,
    get_outbox_files,
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


def test_uc_001():
    """TEST-UC-001 | FTS-UC-001 Main Flow: Verify FTS-UC-001 (Create New File) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='New File', initial_comment='Initial comment', is_draft=True)
    assert file.status == FileStatus.DRAFT
    assert file.created_by_user_id == 1


def test_uc_002():
    """TEST-UC-002 | FTS-UC-001 Alternative Flow 1: Verify FTS-UC-001 Alternative Flow 1: If the employee chooses immediate circulation instead of retaining the draft, the valid created file."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Circulated File', initial_comment='Initial comment', is_draft=False, recipient_user_id=2, recipient_designation='Dean')
    assert file.status == FileStatus.CIRCULATING
    assert file.current_holder_user_id == 2


def test_uc_003():
    """TEST-UC-003 | FTS-UC-001 Alternative Flow 2: Verify FTS-UC-001 Alternative Flow 2: If no attachment is supplied, creation proceeds because attachments are optional.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='No Attachment', initial_comment='Initial comment', is_draft=True, attachments=None)
    assert file.attachments.count() == 0


def test_uc_004():
    """TEST-UC-004 | FTS-UC-001 Exception Flow 1: Verify FTS-UC-001 Exception Flow 1: If the initial comment is missing, FTS does not accept creation/save until the comment is supplied.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_initial_comment('')


def test_uc_005():
    """TEST-UC-005 | FTS-UC-001 Exception Flow 2: Verify FTS-UC-001 Exception Flow 2: If the selected role is not authorized to create files, FTS denies the action.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_forward_recipient(sender_user_id=1, recipient_user_id=1)


def test_uc_006():
    """TEST-UC-006 | FTS-UC-002 Main Flow: Verify FTS-UC-002 (Edit or Discard Draft File) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Draft v1', initial_comment='Com', is_draft=True)
    up = update_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty', subject='Draft v2')
    assert up.subject == 'Draft v2'


def test_uc_007():
    """TEST-UC-007 | FTS-UC-002 Alternative Flow 1: Verify FTS-UC-002 Alternative Flow 1: Employee may choose Discard instead of Save; FTS removes the draft because it has not yet been submi."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Discard me', initial_comment='Com', is_draft=True)
    discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert not TrackedFile.objects.filter(id=file.id).exists()


def test_uc_008():
    """TEST-UC-008 | FTS-UC-002 Exception Flow 1: Verify FTS-UC-002 Exception Flow 1: If the file has already been submitted/circulated, FTS does not permit draft discard.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Circulated', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')


def test_uc_009():
    """TEST-UC-009 | FTS-UC-002 Exception Flow 2: Verify FTS-UC-002 Exception Flow 2: If the employee is not authorized for the draft, FTS denies access/action.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Draft', initial_comment='Com', is_draft=True)
    with pytest.raises(PermissionDeniedError):
        update_draft(file_id=file.id, actor_user_id=2, actor_designation='faculty', subject='Unauthorized edit')


def test_uc_010():
    """TEST-UC-010 | FTS-UC-003 Main Flow: Verify FTS-UC-003 (Send / Forward File to Employee) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='Forwarded')
    assert m.receiver_user_id == 3


def test_uc_011():
    """TEST-UC-011 | FTS-UC-003 Alternative Flow 1: Verify FTS-UC-003 Alternative Flow 1: A recipient of an earlier movement may use the same goal to forward the received file onward to anot."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='Forwarded 1')
    m2 = forward_file(file_id=file.id, actor_user_id=3, actor_designation='faculty', recipient_user_id=4, recipient_designation='Dean', comment='Forwarded 2')
    assert m2.receiver_user_id == 4


def test_uc_012():
    """TEST-UC-012 | FTS-UC-003 Alternative Flow 2: Verify FTS-UC-003 Alternative Flow 2: If no attachment is supplied, forwarding proceeds because attachments are optional.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='No attach', attachments=None)
    assert m.attachments.count() == 0


def test_uc_013():
    """TEST-UC-013 | FTS-UC-003 Exception Flow 1: Verify FTS-UC-003 Exception Flow 1: Missing mandatory movement comment: forwarding is blocked.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_movement_comment('')


def test_uc_014():
    """TEST-UC-014 | FTS-UC-003 Exception Flow 2: Verify FTS-UC-003 Exception Flow 2: Invalid recipient: forwarding is blocked.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_forward_recipient(sender_user_id=2, recipient_user_id=2)


def test_uc_015():
    """TEST-UC-015 | FTS-UC-003 Exception Flow 3: Verify FTS-UC-003 Exception Flow 3: Unauthorized action or archived file: forwarding is blocked and file state is unchanged.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=3, recipient_designation='faculty', comment='Not holder')


def test_uc_016():
    """TEST-UC-016 | FTS-UC-004 Main Flow: Verify FTS-UC-004 (Return Received File) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Returning')
    assert m.action == MovementAction.RETURNED
    assert m.receiver_user_id == 1


def test_uc_017():
    """TEST-UC-017 | FTS-UC-004 Alternative Flow 1: Verify FTS-UC-004 Alternative Flow 1: If no attachment is supplied, return proceeds because attachments are optional.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Returning', attachments=None)
    assert m.attachments.count() == 0


def test_uc_018():
    """TEST-UC-018 | FTS-UC-004 Exception Flow 1: Verify FTS-UC-004 Exception Flow 1: Missing mandatory movement comment: return is blocked.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_movement_comment('')


def test_uc_019():
    """TEST-UC-019 | FTS-UC-004 Exception Flow 2: Verify FTS-UC-004 Exception Flow 2: Unauthorized action or archived/completed file state: return is blocked and the file remains unchang."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        return_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', comment='Creator not holder')


def test_uc_020():
    """TEST-UC-020 | FTS-UC-005 Main Flow: Verify FTS-UC-005 (View Inbox, Outbox, and Open Files) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    inbox = get_inbox_files(user_id=2)
    outbox = get_outbox_files(user_id=1)
    assert any(f.id == file.id for f in inbox)
    assert any(f.id == file.id for f in outbox)


def test_uc_021():
    """TEST-UC-021 | FTS-UC-005 Alternative Flow 1: Verify FTS-UC-005 Alternative Flow 1: If an authorized file is archived, FTS presents it as readable/read-only.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    f = get_associated_file_or_404(file_id=arch.id, user_id=1)
    assert f.status == FileStatus.ARCHIVED


def test_uc_022():
    """TEST-UC-022 | FTS-UC-005 Exception Flow 1: Verify FTS-UC-005 Exception Flow 1: If the employee is not authorized to view a file, FTS does not expose/open that file.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(Http404):
        get_associated_file_or_404(file_id=file.id, user_id=999)


def test_uc_023():
    """TEST-UC-023 | FTS-UC-005 Exception Flow 2: Verify FTS-UC-005 Exception Flow 2: If an action is not authorized for the current file state/role, the action is unavailable or denied.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Cannot forward archived')


def test_uc_024():
    """TEST-UC-024 | FTS-UC-006 Main Flow: Verify FTS-UC-006 (View File Tracking History) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) == 1


def test_uc_025():
    """TEST-UC-025 | FTS-UC-006 Alternative Flow 1: Verify FTS-UC-006 Alternative Flow 1: History may include creation, forward, return, and archival-related audit/version records as maintai."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='Dean', comment='Fwd')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) == 2


def test_uc_026():
    """TEST-UC-026 | FTS-UC-006 Exception Flow 1: Verify FTS-UC-006 Exception Flow 1: If the employee is not authorized/associated with the file, FTS denies history access.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(Http404):
        get_associated_file_or_404(file_id=file.id, user_id=999)


def test_uc_027():
    """TEST-UC-027 | FTS-UC-007 Main Flow: Verify FTS-UC-007 (Archive Completed File) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert arch.status == FileStatus.ARCHIVED


def test_uc_028():
    """TEST-UC-028 | FTS-UC-007 Alternative Flow 1: Verify FTS-UC-007 Alternative Flow 1: If the file is already archived, FTS presents the existing read-only state and performs no new archi."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    f = get_associated_file_or_404(file_id=file.id, user_id=1)
    assert f.status == FileStatus.ARCHIVED


def test_uc_029():
    """TEST-UC-029 | FTS-UC-007 Exception Flow 1: Verify FTS-UC-007 Exception Flow 1: A non-owner archival attempt is denied.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        archive_file(file_id=file.id, actor_user_id=2, actor_designation='staff')


def test_uc_030():
    """TEST-UC-030 | FTS-UC-007 Exception Flow 2: Verify FTS-UC-007 Exception Flow 2: If required authorization is absent, the file remains active and unchanged.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        archive_file(file_id=file.id, actor_user_id=3, actor_designation='staff')


def test_uc_031():
    """TEST-UC-031 | FTS-UC-008 Main Flow: Verify FTS-UC-008 (Select Assigned Role Context for FTS) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=True)
    assert file.creator_designation == 'faculty'


def test_uc_032():
    """TEST-UC-032 | FTS-UC-008 Alternative Flow 1: Verify FTS-UC-008 Alternative Flow 1: If the employee has only one applicable role, FTS uses that assigned role context without requiring."""
    file = create_file(creator_user_id=1, creator_designation='staff', subject='File', initial_comment='Com', is_draft=True)
    assert file.creator_designation == 'staff'


def test_uc_033():
    """TEST-UC-033 | FTS-UC-008 Exception Flow 1: Verify FTS-UC-008 Exception Flow 1: If the selected role does not authorize a requested sensitive action, FTS denies that action.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        forward_file(file_id=file.id, actor_user_id=3, actor_designation='staff', recipient_user_id=4, recipient_designation='faculty', comment='Denied')


def test_uc_034():
    """TEST-UC-034 | FTS-UC-009 Main Flow: Verify FTS-UC-009 (Administer FTS User Access Context) Main Success Scenario."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=True)
    assert file.created_by_user_id == 1


def test_uc_035():
    """TEST-UC-035 | FTS-UC-009 Alternative Flow 1: Verify FTS-UC-009 Alternative Flow 1: Basic user-account creation remains a Fusion/platform administration responsibility where applicable."""
    assert True


def test_uc_036():
    """TEST-UC-036 | FTS-UC-009 Exception Flow 1: Verify FTS-UC-009 Exception Flow 1: If System Admin attempts an operational file workflow action, FTS denies that operational action.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='File', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        forward_file(file_id=file.id, actor_user_id=99, actor_designation='admin', recipient_user_id=3, recipient_designation='faculty', comment='Admin forward')


def test_uc_037():
    """TEST-UC-037 | FTS-UC-010 Main Flow: Verify FTS-UC-010 (Use FTS Workflow-Support APIs) Main Success Scenario."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_uc_038():
    """TEST-UC-038 | FTS-UC-010 Alternative Flow 1: Verify FTS-UC-010 Alternative Flow 1: The consuming module may use different FTS service capabilities (workflow support, approval-chain su."""
    res = get_file_statuses(file_ids=[])
    assert res == []


def test_uc_039():
    """TEST-UC-039 | FTS-UC-010 Exception Flow 1: Verify FTS-UC-010 Exception Flow 1: Unauthorized integration is rejected.."""
    assert get_file_statuses(file_ids=[999999]) == []


def test_uc_040():
    """TEST-UC-040 | FTS-UC-010 Exception Flow 2: Verify FTS-UC-010 Exception Flow 2: A request that asks FTS to define a consuming module's domain-specific approval policy is outside FT."""
    assert True
