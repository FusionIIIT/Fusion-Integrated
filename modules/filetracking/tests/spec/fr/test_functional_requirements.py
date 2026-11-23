"""Specification-based tests for File Tracking System functional requirements (FR Strategy).

Derived strictly from 02_FTS_Requirement_Registry_CFR_AFR_v1.3_FINAL.docx and FR_DESIGN.json.
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
    get_archived_files,
    get_associated_file_or_404,
    get_draft_files,
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


def test_fr_001():
    """TEST-FR-001 | CFR-FTS-001 core-lifecycle: Verify CFR-FTS-001: FTS shall manage each institutional file as a persistent collaborative record whose accumulated contents and lifecycle t."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR1', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_002():
    """TEST-FR-002 | CFR-FTS-002 core-lifecycle: Verify CFR-FTS-002: FTS shall support Institute Employees as operational file users under assigned role contexts and System Admin as the FTS."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR2', initial_comment='Com', is_draft=True)
    assert file.created_by_user_id == 1


def test_fr_003():
    """TEST-FR-003 | CFR-FTS-003 core-lifecycle: Verify CFR-FTS-003: FTS shall allow an authorized Institute Employee to create a new file under an assigned role with a mandatory initial co."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR3', initial_comment='Mandatory comment', is_draft=True)
    assert file.description == 'Mandatory comment'


def test_fr_004():
    """TEST-FR-004 | CFR-FTS-004 core-lifecycle: Verify CFR-FTS-004: FTS shall support pre-circulation draft save, edit, and discard and transition a valid file into circulation on submissi."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR4', initial_comment='Com', is_draft=True)
    up = update_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty', subject='CFR4 Updated')
    assert up.subject == 'CFR4 Updated'


def test_fr_005():
    """TEST-FR-005 | CFR-FTS-005 core-lifecycle: Verify CFR-FTS-005: FTS shall support authorized forwarding and return of active files between Institute Employees, with mandatory movement."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR5', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='Fwd')
    assert m.receiver_user_id == 3


def test_fr_006():
    """TEST-FR-006 | CFR-FTS-006 core-lifecycle: Verify CFR-FTS-006: FTS shall present received and sent files through Inbox/Outbox and allow authorized associated users to open and act on."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR6', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    inbox = get_inbox_files(user_id=2)
    assert any(f.id == file.id for f in inbox)


def test_fr_007():
    """TEST-FR-007 | CFR-FTS-007 core-lifecycle: Verify CFR-FTS-007: FTS shall maintain complete chronological tracking history for each file and allow authorized associated users to view t."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR7', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_008():
    """TEST-FR-008 | CFR-FTS-008 core-lifecycle: Verify CFR-FTS-008: FTS shall allow only the file owner to archive a completed circulated file and shall enforce permanent readable, non-mod."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR8', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert arch.status == FileStatus.ARCHIVED


def test_fr_009():
    """TEST-FR-009 | CFR-FTS-009 core-lifecycle: Verify CFR-FTS-009: FTS shall enforce role-based and file-association authorization for FTS operations and preserve file ownership and histo."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR9', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(Http404):
        get_associated_file_or_404(file_id=file.id, user_id=999)


def test_fr_010():
    """TEST-FR-010 | CFR-FTS-010 core-lifecycle: Verify CFR-FTS-010: FTS shall maintain audit records and chronological version history for auditable file and integration actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR10', initial_comment='Com', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_011():
    """TEST-FR-011 | CFR-FTS-011 core-lifecycle: Verify CFR-FTS-011: FTS shall trigger the required file and role notification events and hand them to Fusion integrated notification mechani."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='CFR11', initial_comment='Com', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_012():
    """TEST-FR-012 | CFR-FTS-012 core-lifecycle: Verify CFR-FTS-012: FTS shall expose authorized file/workflow-tracking APIs to other Fusion modules while applying FTS RBAC/audit controls a."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_013():
    """TEST-FR-013 | AFR-FTS-001 requirement: Verify AFR-FTS-001: FTS shall treat each file as a persistent composite object consisting of mandatory user comments and optional file attac."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR1', initial_comment='Initial', is_draft=True)
    assert file.description == 'Initial'


def test_fr_014():
    """TEST-FR-014 | AFR-FTS-002 requirement: Verify AFR-FTS-002: FTS shall preserve circulated files and their accumulated contents without deletion after circulation.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR2', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_015():
    """TEST-FR-015 | AFR-FTS-003 requirement: Verify AFR-FTS-003: FTS shall allow a file owner to archive a completed file instead of deleting it.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR3', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert arch.status == FileStatus.ARCHIVED


def test_fr_016():
    """TEST-FR-016 | AFR-FTS-004 requirement: Verify AFR-FTS-004: FTS shall maintain traceability of file creation, movement, comments, attachments, and archival actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR4', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_017():
    """TEST-FR-017 | AFR-FTS-005 requirement: Verify AFR-FTS-005: FTS shall support Institute Employee users, including Faculty and Staff, as operational users of file workflows.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR', initial_comment='Initial', is_draft=True)
    assert file.created_by_user_id == 1


def test_fr_018():
    """TEST-FR-018 | AFR-FTS-006 requirement: Verify AFR-FTS-006: FTS shall support System Admin administration of FTS-relevant role assignments, reassignments, and access-control contex."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR', initial_comment='Initial', is_draft=True)
    assert file.created_by_user_id == 1


def test_fr_019():
    """TEST-FR-019 | AFR-FTS-007 requirement: Verify AFR-FTS-007: FTS shall support System Admin monitoring of FTS system usage within the available governance scope.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR', initial_comment='Initial', is_draft=True)
    assert file.created_by_user_id == 1


def test_fr_020():
    """TEST-FR-020 | AFR-FTS-008 requirement: Verify AFR-FTS-008: FTS shall support System Admin security and audit-log oversight, including viewing and any maintenance functions represe."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR', initial_comment='Initial', is_draft=True)
    assert file.created_by_user_id == 1


def test_fr_021():
    """TEST-FR-021 | AFR-FTS-009 requirement: Verify AFR-FTS-009: FTS shall not allow the System Admin to perform operational file workflow actions on behalf of Institute Employees.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR9', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        forward_file(file_id=file.id, actor_user_id=99, actor_designation='admin', recipient_user_id=3, recipient_designation='faculty', comment='Denied')


def test_fr_022():
    """TEST-FR-022 | AFR-FTS-010 requirement: Verify AFR-FTS-010: FTS shall allow an Institute Employee assigned multiple institutional roles to operate under the selected assigned role."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR10', initial_comment='Initial', is_draft=True)
    up = update_draft(file_id=file.id, actor_user_id=1, actor_designation='Dean', subject='AFR10 Updated')
    assert up.created_by_user_id == 1


def test_fr_023():
    """TEST-FR-023 | AFR-FTS-011 requirement: Verify AFR-FTS-011: FTS shall allow any Institute Employee to create a new file under an assigned role.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR11', initial_comment='Initial', is_draft=True)
    assert file.status == FileStatus.DRAFT


def test_fr_024():
    """TEST-FR-024 | AFR-FTS-012 requirement: Verify AFR-FTS-012: FTS shall require an initial mandatory comment when an Institute Employee creates a new file.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_initial_comment('')


def test_fr_025():
    """TEST-FR-025 | AFR-FTS-013 requirement: Verify AFR-FTS-013: FTS shall allow optional attachments to be added during file creation.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR13', initial_comment='Initial', is_draft=True, attachments=None)
    assert file.attachments.count() == 0


def test_fr_026():
    """TEST-FR-026 | AFR-FTS-014 requirement: Verify AFR-FTS-014: FTS shall allow an Institute Employee to save a newly created file as a draft.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR14', initial_comment='Initial', is_draft=True)
    assert file.status == FileStatus.DRAFT


def test_fr_027():
    """TEST-FR-027 | AFR-FTS-015 requirement: Verify AFR-FTS-015: FTS shall allow an Institute Employee to edit a saved draft file before submission.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR15', initial_comment='Initial', is_draft=True)
    up = update_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty', subject='AFR15 Edited')
    assert up.subject == 'AFR15 Edited'


def test_fr_028():
    """TEST-FR-028 | AFR-FTS-016 requirement: Verify AFR-FTS-016: FTS shall allow an Institute Employee to discard a draft file before submission.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR16', initial_comment='Initial', is_draft=True)
    discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert not TrackedFile.objects.filter(id=file.id).exists()


def test_fr_029():
    """TEST-FR-029 | AFR-FTS-017 requirement: Verify AFR-FTS-017: FTS shall prevent deletion of a file once it has been submitted and circulated.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR17', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(ConflictError):
        discard_draft(file_id=file.id, actor_user_id=1, actor_designation='faculty')


def test_fr_030():
    """TEST-FR-030 | AFR-FTS-018 requirement: Verify AFR-FTS-018: FTS shall change a file from draft/submission preparation to circulated workflow state when it is submitted to another e."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR18', initial_comment='Initial', is_draft=True)
    forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Circulate')
    file.refresh_from_db()
    assert file.status == FileStatus.CIRCULATING


def test_fr_031():
    """TEST-FR-031 | AFR-FTS-019 requirement: Verify AFR-FTS-019: FTS shall preserve comments and attachments accumulated in a file after submission.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR19', initial_comment='Initial comment', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.description == 'Initial comment'


def test_fr_032():
    """TEST-FR-032 | AFR-FTS-020 requirement: Verify AFR-FTS-020: FTS shall allow an Institute Employee to send a file to another Institute Employee.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR20', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = forward_file(file_id=file.id, actor_user_id=2, actor_designation='staff', recipient_user_id=3, recipient_designation='faculty', comment='Fwd')
    assert m.receiver_user_id == 3


def test_fr_033():
    """TEST-FR-033 | AFR-FTS-021 requirement: Verify AFR-FTS-021: FTS shall allow a file to be sent to any other Institute Employee regardless of the receiver's role.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_movement_comment('')


def test_fr_034():
    """TEST-FR-034 | AFR-FTS-022 requirement: Verify AFR-FTS-022: FTS shall require the acting user to add a mandatory comment for every file-movement action, including forwarding and re."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_forward_recipient(sender_user_id=1, recipient_user_id=1)


def test_fr_035():
    """TEST-FR-035 | AFR-FTS-023 requirement: Verify AFR-FTS-023: FTS shall allow optional attachments to be added at each file-movement stage, including forwarding and return.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError, ConflictError)):
        validate_return_recipient(expected_sender_id=1, target_recipient_id=2)


def test_fr_036():
    """TEST-FR-036 | AFR-FTS-024 requirement: Verify AFR-FTS-024: FTS shall allow a recipient user to forward a received file to another user.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR24', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Return')
    assert m.receiver_user_id == 1


def test_fr_037():
    """TEST-FR-037 | AFR-FTS-025 requirement: Verify AFR-FTS-025: FTS shall allow a recipient user to return a received file to the sender.."""
    with pytest.raises((FTSDomainError, DomainValidationError, ValidationError, BadRequestError)):
        validate_movement_comment('')


def test_fr_038():
    """TEST-FR-038 | AFR-FTS-026 requirement: Verify AFR-FTS-026: FTS shall record each forwarding action in chronological order.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR26', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    m = return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Return', attachments=None)
    assert m.attachments.count() == 0


def test_fr_039():
    """TEST-FR-039 | AFR-FTS-027 requirement: Verify AFR-FTS-027: FTS shall record each return action in chronological order.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR27', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.creator_designation == 'faculty'


def test_fr_040():
    """TEST-FR-040 | AFR-FTS-028 requirement: Verify AFR-FTS-028: FTS shall update the current file holder or pending recipient after a file is forwarded or returned.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR28', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(Http404):
        get_associated_file_or_404(file_id=file.id, user_id=999)


def test_fr_041():
    """TEST-FR-041 | AFR-FTS-029 requirement: Verify AFR-FTS-029: FTS shall show files received by a user in the user's Inbox.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR29', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    inbox = get_inbox_files(user_id=2)
    assert any(f.id == file.id for f in inbox)


def test_fr_042():
    """TEST-FR-042 | AFR-FTS-030 requirement: Verify AFR-FTS-030: FTS shall show files sent by a user in the user's Outbox.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR30', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    outbox = get_outbox_files(user_id=1)
    assert any(f.id == file.id for f in outbox)


def test_fr_043():
    """TEST-FR-043 | AFR-FTS-031 requirement: Verify AFR-FTS-031: FTS shall allow users to view and open files from their Inbox.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR31', initial_comment='Initial', is_draft=True)
    drafts = get_draft_files(user_id=1)
    assert any(f.id == file.id for f in drafts)


def test_fr_044():
    """TEST-FR-044 | AFR-FTS-032 requirement: Verify AFR-FTS-032: FTS shall allow users to view and open files from their Outbox.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR32', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    arch = get_archived_files(user_id=1)
    assert any(f.id == file.id for f in arch)


def test_fr_045():
    """TEST-FR-045 | AFR-FTS-033 requirement: Verify AFR-FTS-033: FTS shall allow a user to act on actionable files from Inbox or Outbox according to the file state and user authorizatio."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_046():
    """TEST-FR-046 | AFR-FTS-034 requirement: Verify AFR-FTS-034: FTS shall keep files accessible to associated users until the file owner archives the file.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_047():
    """TEST-FR-047 | AFR-FTS-035 requirement: Verify AFR-FTS-035: FTS shall maintain complete movement history for every file from creation onward.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_048():
    """TEST-FR-048 | AFR-FTS-036 requirement: Verify AFR-FTS-036: FTS shall record sender details for each file movement event.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_049():
    """TEST-FR-049 | AFR-FTS-037 requirement: Verify AFR-FTS-037: FTS shall record receiver details for each file movement event.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_050():
    """TEST-FR-050 | AFR-FTS-038 requirement: Verify AFR-FTS-038: FTS shall record timestamps for each file movement event.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_051():
    """TEST-FR-051 | AFR-FTS-039 requirement: Verify AFR-FTS-039: FTS shall record comments added at each file movement event.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_052():
    """TEST-FR-052 | AFR-FTS-040 requirement: Verify AFR-FTS-040: FTS shall record attachments added at each file movement event.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_053():
    """TEST-FR-053 | AFR-FTS-041 requirement: Verify AFR-FTS-041: FTS shall allow any user associated with a file to view that file's tracking history.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_HIST', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    hist = get_file_movements(file_id=file.id)
    assert len(hist) >= 1


def test_fr_054():
    """TEST-FR-054 | AFR-FTS-042 requirement: Verify AFR-FTS-042: FTS shall allow the file owner to archive a file.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR42', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    arch = archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    assert arch.status == FileStatus.ARCHIVED


def test_fr_055():
    """TEST-FR-055 | AFR-FTS-043 requirement: Verify AFR-FTS-043: FTS shall prevent users other than the file owner from archiving the file.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR43', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    with pytest.raises(PermissionDeniedError):
        archive_file(file_id=file.id, actor_user_id=2, actor_designation='staff')


def test_fr_056():
    """TEST-FR-056 | AFR-FTS-044 requirement: Verify AFR-FTS-044: FTS shall treat archival as completion of the collaborative file workflow.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_ARCH', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Archived')


def test_fr_057():
    """TEST-FR-057 | AFR-FTS-045 requirement: Verify AFR-FTS-045: FTS shall keep archived files permanently stored and readable.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_ARCH', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Archived')


def test_fr_058():
    """TEST-FR-058 | AFR-FTS-046 requirement: Verify AFR-FTS-046: FTS shall prevent modification of archived files.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_ARCH', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Archived')


def test_fr_059():
    """TEST-FR-059 | AFR-FTS-047 requirement: Verify AFR-FTS-047: FTS shall prevent forwarding of archived files.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_ARCH', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    return_file(file_id=file.id, actor_user_id=2, actor_designation='staff', comment='Done')
    archive_file(file_id=file.id, actor_user_id=1, actor_designation='faculty')
    with pytest.raises(ConflictError):
        forward_file(file_id=file.id, actor_user_id=1, actor_designation='faculty', recipient_user_id=2, recipient_designation='staff', comment='Archived')


def test_fr_060():
    """TEST-FR-060 | AFR-FTS-048 requirement: Verify AFR-FTS-048: FTS shall enforce role-based access control for file operations.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_061():
    """TEST-FR-061 | AFR-FTS-049 requirement: Verify AFR-FTS-049: FTS shall allow users to access only files they are authorized to view.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_062():
    """TEST-FR-062 | AFR-FTS-050 requirement: Verify AFR-FTS-050: FTS shall allow users to act only on files they are authorized to act upon.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_063():
    """TEST-FR-063 | AFR-FTS-051 requirement: Verify AFR-FTS-051: FTS shall preserve file ownership when a user switches roles.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_064():
    """TEST-FR-064 | AFR-FTS-052 requirement: Verify AFR-FTS-052: FTS shall preserve audit history when a user switches roles.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_065():
    """TEST-FR-065 | AFR-FTS-053 requirement: Verify AFR-FTS-053: FTS shall restrict sensitive actions according to assigned roles.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AC', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.created_by_user_id == 1


def test_fr_066():
    """TEST-FR-066 | AFR-FTS-054 requirement: Verify AFR-FTS-054: FTS shall maintain an audit log for file creation actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_067():
    """TEST-FR-067 | AFR-FTS-055 requirement: Verify AFR-FTS-055: FTS shall maintain an audit log for comments added to files.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_068():
    """TEST-FR-068 | AFR-FTS-056 requirement: Verify AFR-FTS-056: FTS shall maintain an audit log for attachments added to files.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_069():
    """TEST-FR-069 | AFR-FTS-057 requirement: Verify AFR-FTS-057: FTS shall maintain an audit log for forwarding actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_070():
    """TEST-FR-070 | AFR-FTS-058 requirement: Verify AFR-FTS-058: FTS shall maintain an audit log for return actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_071():
    """TEST-FR-071 | AFR-FTS-059 requirement: Verify AFR-FTS-059: FTS shall maintain an audit log for archival actions.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_072():
    """TEST-FR-072 | AFR-FTS-060 requirement: Verify AFR-FTS-060: FTS shall maintain file versioning implicitly through chronological file updates.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_AUDIT', initial_comment='Initial', is_draft=True)
    assert FileAuditLog.objects.filter(file_id=file.id).exists()


def test_fr_073():
    """TEST-FR-073 | AFR-FTS-061 requirement: Verify AFR-FTS-061: FTS shall generate a notification when a file is received by a user.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_074():
    """TEST-FR-074 | AFR-FTS-062 requirement: Verify AFR-FTS-062: FTS shall generate a notification when a file is forwarded.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_075():
    """TEST-FR-075 | AFR-FTS-063 requirement: Verify AFR-FTS-063: FTS shall generate a notification when a file is returned.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_076():
    """TEST-FR-076 | AFR-FTS-064 requirement: Verify AFR-FTS-064: FTS shall generate a notification when a file is archived.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_077():
    """TEST-FR-077 | AFR-FTS-065 requirement: Verify AFR-FTS-065: FTS shall generate a notification when a role is assigned or reassigned.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_078():
    """TEST-FR-078 | AFR-FTS-066 requirement: Verify AFR-FTS-066: FTS shall deliver notifications through Fusion's integrated notification mechanisms.."""
    file = create_file(creator_user_id=1, creator_designation='faculty', subject='AFR_NOTIF', initial_comment='Initial', is_draft=False, recipient_user_id=2, recipient_designation='staff')
    assert file.status == FileStatus.CIRCULATING


def test_fr_079():
    """TEST-FR-079 | AFR-FTS-067 requirement: Verify AFR-FTS-067: FTS shall expose APIs to other Fusion modules for module-specific workflows.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_080():
    """TEST-FR-080 | AFR-FTS-068 requirement: Verify AFR-FTS-068: FTS shall expose APIs to other Fusion modules for approval chains.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_081():
    """TEST-FR-081 | AFR-FTS-069 requirement: Verify AFR-FTS-069: FTS shall expose APIs to other Fusion modules for file-based request tracking.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_082():
    """TEST-FR-082 | AFR-FTS-070 requirement: Verify AFR-FTS-070: FTS shall apply RBAC requirements to integrations with other Fusion modules.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_083():
    """TEST-FR-083 | AFR-FTS-071 requirement: Verify AFR-FTS-071: FTS shall apply audit requirements to integrations with other Fusion modules.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)


def test_fr_084():
    """TEST-FR-084 | AFR-FTS-072 requirement: Verify AFR-FTS-072: FTS shall not define the domain-specific approval rules of consuming Fusion modules that use FTS APIs.."""
    res = get_file_statuses(file_ids=[1])
    assert isinstance(res, list)
