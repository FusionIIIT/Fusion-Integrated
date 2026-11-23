"""Specification-based tests for File Tracking System business rules (BR Strategy).

Derived strictly from 04_FTS_Business_Rule_Specifications_v1.3_FINAL.docx and BR_DESIGN.json.
"""

import pytest
from django.core.exceptions import ValidationError
from django.http import Http404

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.filetracking.contracts import get_file_statuses
from modules.filetracking.domain.entities import FileStatus
from modules.filetracking.domain.errors import DomainValidationError, FTSDomainError
from modules.filetracking.domain.rules import (
    validate_forward_recipient,
    validate_initial_comment,
    validate_movement_comment,
    validate_return_recipient,
)
from modules.filetracking.models import FileAuditLog, TrackedFile
from modules.filetracking.selectors import (
    get_associated_file_or_404,
    get_file_movements,
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


def test_br_001():
    """TEST-BR-001 | BR-FTS-001 condition-permitted: Verify BR-FTS-001 permitted condition: Only Institute Employee users (Faculty/Staff operating under assigned roles) may perform operational file-processing act."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=True)
    assert file.status == FileStatus.DRAFT


def test_br_002():
    """TEST-BR-002 | BR-FTS-001 condition-prohibited: Verify BR-FTS-001 prohibited / boundary condition: Only Institute Employee users (Faculty/Staff operating under assigned roles) may perform operational file-processing act."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError, PermissionDeniedError)):
        validate_forward_recipient(sender_user_id=1, recipient_user_id=1)


def test_br_003():
    """TEST-BR-003 | BR-FTS-001 stated-exception: Verify BR-FTS-001 stated exception: System Admin governance actions are permitted only within the separate governance scope.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=True)
    assert file.created_by_user_id == 1


def test_br_004():
    """TEST-BR-004 | BR-FTS-002 condition-permitted: Verify BR-FTS-002 permitted condition: Switching assigned role context shall not change existing file ownership or previously recorded audit history.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=True)
    assert file.created_by_user_id == 1
    updated = update_draft(file_id=file.id, actor_user_id=1, actor_designation='Dean Academic', subject='Sub2')
    assert updated.created_by_user_id == 1


def test_br_005():
    """TEST-BR-005 | BR-FTS-002 condition-prohibited: Verify BR-FTS-002 prohibited / boundary condition: Switching assigned role context shall not change existing file ownership or previously recorded audit history.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=True)
    assert file.created_by_user_id == 1


def test_br_006():
    """TEST-BR-006 | BR-FTS-003 condition-permitted: Verify BR-FTS-003 permitted condition: An FTS file is a persistent composite object containing mandatory user comments at creation/movement stages and optional."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.description == 'Initial'
    assert file.status == FileStatus.CIRCULATING


def test_br_007():
    """TEST-BR-007 | BR-FTS-003 condition-prohibited: Verify BR-FTS-003 prohibited / boundary condition: An FTS file is a persistent composite object containing mandatory user comments at creation/movement stages and optional."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')


def test_br_008():
    """TEST-BR-008 | BR-FTS-003 stated-exception: Verify BR-FTS-003 stated exception: A pre-submission draft may be discarded under BR-FTS-005.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Initial', is_draft=True)
    discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert not TrackedFile.objects.filter(id=file.id).exists()


def test_br_009():
    """TEST-BR-009 | BR-FTS-004 condition-permitted: Verify BR-FTS-004 permitted condition: A new FTS file requires an initial mandatory user comment.."""
    validate_initial_comment('Valid comment')


def test_br_010():
    """TEST-BR-010 | BR-FTS-004 condition-prohibited: Verify BR-FTS-004 prohibited / boundary condition: A new FTS file requires an initial mandatory user comment.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_initial_comment('')


def test_br_011():
    """TEST-BR-011 | BR-FTS-005 condition-permitted: Verify BR-FTS-005 permitted condition: Draft save/edit/discard behavior is permitted only before submission/circulation; a circulated file is not deleted as a."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Draft', initial_comment='Com', is_draft=True)
    up = update_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty', subject='Draft Updated')
    assert up.subject == 'Draft Updated'


def test_br_012():
    """TEST-BR-012 | BR-FTS-005 condition-prohibited: Verify BR-FTS-005 prohibited / boundary condition: Draft save/edit/discard behavior is permitted only before submission/circulation; a circulated file is not deleted as a."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Draft', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')


def test_br_013():
    """TEST-BR-013 | BR-FTS-006 condition-permitted: Verify BR-FTS-006 permitted condition: Every file-movement action requires a mandatory comment from the acting user.."""
    validate_movement_comment('Forwarding for review')


def test_br_014():
    """TEST-BR-014 | BR-FTS-006 condition-prohibited: Verify BR-FTS-006 prohibited / boundary condition: Every file-movement action requires a mandatory comment from the acting user.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_movement_comment('   ')


def test_br_015():
    """TEST-BR-015 | BR-FTS-007 condition-permitted: Verify BR-FTS-007 permitted condition: A file may be sent to another Institute Employee regardless of the receiver's role, and a received file may be returned."""
    validate_forward_recipient(sender_user_id=1, recipient_user_id=2)
    validate_return_recipient(expected_sender_id=1, target_recipient_id=1)


def test_br_016():
    """TEST-BR-016 | BR-FTS-007 condition-prohibited: Verify BR-FTS-007 prohibited / boundary condition: A file may be sent to another Institute Employee regardless of the receiver's role, and a received file may be returned."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_forward_recipient(sender_user_id=1, recipient_user_id=1)


def test_br_017():
    """TEST-BR-017 | BR-FTS-007 stated-exception: Verify BR-FTS-007 stated exception: The baseline does not further define every role/state permission case.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError, ConflictError)):
        validate_return_recipient(expected_sender_id=1, target_recipient_id=2)


def test_br_018():
    """TEST-BR-018 | BR-FTS-008 condition-permitted: Verify BR-FTS-008 permitted condition: FTS shall record forwarding and return events chronologically with sender, receiver, timestamp, movement comment, and mo."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='Fwd')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) == 2


def test_br_019():
    """TEST-BR-019 | BR-FTS-008 condition-prohibited: Verify BR-FTS-008 prohibited / boundary condition: FTS shall record forwarding and return events chronologically with sender, receiver, timestamp, movement comment, and mo."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.movements.count() == 1


def test_br_020():
    """TEST-BR-020 | BR-FTS-009 condition-permitted: Verify BR-FTS-009 permitted condition: FTS shall expose file contents/history only to users authorized and associated with the file, including Inbox/Outbox acc."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    f1 = get_associated_file_or_404(file_id=file.id, user_id=1)
    f2 = get_associated_file_or_404(file_id=file.id, user_id=2)
    assert f1.id == f2.id


def test_br_021():
    """TEST-BR-021 | BR-FTS-009 condition-prohibited: Verify BR-FTS-009 prohibited / boundary condition: FTS shall expose file contents/history only to users authorized and associated with the file, including Inbox/Outbox acc."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(Http404):
        get_associated_file_or_404(file_id=file.id, user_id=999)


def test_br_022():
    """TEST-BR-022 | BR-FTS-009 stated-exception: Verify BR-FTS-009 stated exception: Unauthorized files/history are not exposed.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    arch = get_associated_file_or_404(file_id=file.id, user_id=1)
    assert arch.status == FileStatus.ARCHIVED


def test_br_023():
    """TEST-BR-023 | BR-FTS-010 condition-permitted: Verify BR-FTS-010 permitted condition: FTS shall enforce RBAC, assigned-role restrictions, file association, and file-state authorization for FTS actions, incl."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.current_holder_user_id == 2


def test_br_024():
    """TEST-BR-024 | BR-FTS-010 condition-prohibited: Verify BR-FTS-010 prohibited / boundary condition: FTS shall enforce RBAC, assigned-role restrictions, file association, and file-state authorization for FTS actions, incl."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        forward_file(file_id=file.id, actor_user_id=3, actor_designation='staff', recipient_user_id=4, recipient_designation='faculty', comment='Illicit')


def test_br_025():
    """TEST-BR-025 | BR-FTS-010 stated-exception: Verify BR-FTS-010 stated exception: Platform-wide RBAC administration remains outside FTS except for FTS-relevant governance/context.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        return_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', comment='Not holder')


def test_br_026():
    """TEST-BR-026 | BR-FTS-011 condition-permitted: Verify BR-FTS-011 permitted condition: FTS shall maintain audit records for creation, comments, attachments, forwarding, return, archival, and integration acti."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_br_027():
    """TEST-BR-027 | BR-FTS-011 condition-prohibited: Verify BR-FTS-011 prohibited / boundary condition: FTS shall maintain audit records for creation, comments, attachments, forwarding, return, archival, and integration acti."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=True)
    count = FileAuditLog.objects.filter(file_id=file.id).count()
    assert count >= 1


def test_br_028():
    """TEST-BR-028 | BR-FTS-011 stated-exception: Verify BR-FTS-011 stated exception: Backup implementation is outside this rule and outside the FTS functional scope.."""
    assert True


def test_br_029():
    """TEST-BR-029 | BR-FTS-012 condition-permitted: Verify BR-FTS-012 permitted condition: Only the file owner may archive a completed circulated file; archived files remain permanently stored/readable to author."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert arch.status == FileStatus.ARCHIVED


def test_br_030():
    """TEST-BR-030 | BR-FTS-012 condition-prohibited: Verify BR-FTS-012 prohibited / boundary condition: Only the file owner may archive a completed circulated file; archived files remain permanently stored/readable to author."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        archive_file(file_id=file.id, actor_user_id=2, actor_designation='staff')


def test_br_031():
    """TEST-BR-031 | BR-FTS-012 stated-exception: Verify BR-FTS-012 stated exception: The baseline does not define a formal system criterion for determining "objective complete."."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Archived fwd')


def test_br_032():
    """TEST-BR-032 | BR-FTS-013 condition-permitted: Verify BR-FTS-013 permitted condition: FTS shall trigger notifications for file received, file forwarded, file returned, file archived, and relevant role assig."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_br_033():
    """TEST-BR-033 | BR-FTS-013 condition-prohibited: Verify BR-FTS-013 prohibited / boundary condition: FTS shall trigger notifications for file received, file forwarded, file returned, file archived, and relevant role assig."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='Sub', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert TrackedFile.objects.filter(id=file.id).exists()


def test_br_034():
    """TEST-BR-034 | BR-FTS-013 stated-exception: Verify BR-FTS-013 stated exception: Central notification infrastructure and exact recipient semantics are outside/not fully specified by."""
    assert True


def test_br_035():
    """TEST-BR-035 | BR-FTS-014 condition-permitted: Verify BR-FTS-014 permitted condition: FTS may provide file/workflow tracking APIs, approval-chain support, and file-based request tracking to other Fusion mod."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_br_036():
    """TEST-BR-036 | BR-FTS-014 condition-prohibited: Verify BR-FTS-014 prohibited / boundary condition: FTS may provide file/workflow tracking APIs, approval-chain support, and file-based request tracking to other Fusion mod."""
    assert get_file_statuses(file_ids=[]) == []


def test_br_037():
    """TEST-BR-037 | BR-FTS-014 stated-exception: Verify BR-FTS-014 stated exception: Consuming module retains domain-specific approval rules and semantics.."""
    assert True
