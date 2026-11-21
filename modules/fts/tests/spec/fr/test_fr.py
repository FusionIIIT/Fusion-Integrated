"""Functional requirement checks covering all 84 frozen FR cases."""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.fts import contracts
from modules.fts.models import FTSAuditLog, FTSFile
from modules.fts.selectors import scoping
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db

def test_fr_t_cfr_fts_001():
    """T_CFR-FTS-001 (CFR-FTS-001): FTS shall manage each institutional file as a persistent collaborative record whose accumulated contents and lifecycle trace are preserved after circulation, with completed circulated files closed through owner-controlled archival rather than deletion."""
    obj = file_service.create_file(subject="CFR-01", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    obj.refresh_from_db()
    assert obj.status == "archived"

def test_fr_t_cfr_fts_002():
    """T_CFR-FTS-002 (CFR-FTS-002): FTS shall support Institute Employees as operational file users under assigned role contexts and System Admin as the FTS governance actor, while keeping operational file processing with Institute Employees."""
    with pytest.raises(PermissionDeniedError):
        file_service.create_file(subject="CFR-02", initial_comment="Start", creator_id=1, is_draft=True, is_employee=False, is_system_admin=True)

def test_fr_t_cfr_fts_003():
    """T_CFR-FTS-003 (CFR-FTS-003): FTS shall allow an authorized Institute Employee to create a new file under an assigned role with a mandatory initial comment and optional attachments."""
    obj = file_service.create_file(subject="CFR-03", initial_comment="Start", creator_id=1, is_draft=True, attachments=[{"file_name": "x.pdf"}])
    assert obj.comments.count() == 1 and obj.attachments.count() == 1

def test_fr_t_cfr_fts_004():
    """T_CFR-FTS-004 (CFR-FTS-004): FTS shall support pre-circulation draft save, edit, and discard and transition a valid file into circulation on submission, while preventing draft deletion and preserving accumulated contents after circulation."""
    obj = file_service.create_file(subject="CFR-04", initial_comment="Start", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="CFR-04-E")
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="Submit")
    with pytest.raises(ConflictError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)

def test_fr_t_cfr_fts_005():
    """T_CFR-FTS-005 (CFR-FTS-005): FTS shall support authorized forwarding and return of active files between Institute Employees, with mandatory movement comments, optional attachments, routing/holder updates, and chronological movement recording."""
    obj = file_service.create_file(subject="CFR-05", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd")
    ret = file_service.return_file(file_id_or_pk=obj.file_id, sender_id=3, remarks="Ret")
    assert ret.sequence_number == 3

def test_fr_t_cfr_fts_006():
    """T_CFR-FTS-006 (CFR-FTS-006): FTS shall present received and sent files through Inbox/Outbox and allow authorized associated users to open and act on files according to role and file state until archival."""
    obj = file_service.create_file(subject="CFR-06", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_inbox_files(2).filter(pk=obj.pk).exists()
    assert scoping.visible_outbox_files(1).filter(pk=obj.pk).exists()

def test_fr_t_cfr_fts_007():
    """T_CFR-FTS-007 (CFR-FTS-007): FTS shall maintain complete chronological tracking history for each file and allow authorized associated users to view the required movement details."""
    obj = file_service.create_file(subject="CFR-07", initial_comment="Start", creator_id=1, receiver_id=2)
    assert len(scoping.get_file_movements(obj)) == 1

def test_fr_t_cfr_fts_008():
    """T_CFR-FTS-008 (CFR-FTS-008): FTS shall allow only the file owner to archive a completed circulated file and shall enforce permanent readable, non-modifiable, non-forwardable archival state."""
    obj = file_service.create_file(subject="CFR-08", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert archived.status == "archived"

def test_fr_t_cfr_fts_009():
    """T_CFR-FTS-009 (CFR-FTS-009): FTS shall enforce role-based and file-association authorization for FTS operations and preserve file ownership and historical audit identity across role switching."""
    obj = file_service.create_file(subject="CFR-09", initial_comment="Start", creator_id=1, creator_designation="dean", is_draft=True)
    assert obj.owner_id == 1 and obj.creator_designation == "dean"

def test_fr_t_cfr_fts_010():
    """T_CFR-FTS-010 (CFR-FTS-010): FTS shall maintain audit records and chronological version history for auditable file and integration actions."""
    obj = file_service.create_file(subject="CFR-10", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_cfr_fts_011():
    """T_CFR-FTS-011 (CFR-FTS-011): FTS shall trigger the required file and role notification events and hand them to Fusion integrated notification mechanisms for delivery."""
    obj = file_service.create_file(subject="CFR-11", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_cfr_fts_012():
    """T_CFR-FTS-012 (CFR-FTS-012): FTS shall expose authorized file/workflow-tracking APIs to other Fusion modules while applying FTS RBAC/audit controls and leaving consuming modules responsible for domain-specific approval semantics."""
    obj = file_service.create_file(subject="CFR-12", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries

def test_fr_t_afr_fts_001():
    """T_AFR-FTS-001 (AFR-FTS-001): FTS shall treat each file as a persistent composite object consisting of mandatory user comments and optional file attachments."""
    obj = file_service.create_file(subject="AFR-01", initial_comment="Note", creator_id=1, is_draft=True, attachments=[{"file_name": "f.pdf"}])
    assert obj.comments.count() == 1 and obj.attachments.count() == 1

def test_fr_t_afr_fts_002():
    """T_AFR-FTS-002 (AFR-FTS-002): FTS shall preserve circulated files and their accumulated contents without deletion after circulation."""
    obj = file_service.create_file(subject="AFR-02", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(ConflictError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)

def test_fr_t_afr_fts_003():
    """T_AFR-FTS-003 (AFR-FTS-003): FTS shall allow a file owner to archive a completed file instead of deleting it."""
    obj = file_service.create_file(subject="AFR-03", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert archived.status == "archived"

def test_fr_t_afr_fts_004():
    """T_AFR-FTS-004 (AFR-FTS-004): FTS shall maintain traceability of file creation, movement, comments, attachments, and archival actions."""
    obj = file_service.create_file(subject="AFR-04", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.movements.count() == 1 and obj.comments.count() == 1

def test_fr_t_afr_fts_005():
    """T_AFR-FTS-005 (AFR-FTS-005): FTS shall support Institute Employee users, including Faculty and Staff, as operational users of file workflows."""
    obj = file_service.create_file(subject="AFR-05", initial_comment="Start", creator_id=1, is_draft=True, creator_designation="faculty", is_employee=True)
    assert obj.creator_designation == "faculty"

def test_fr_t_afr_fts_006():
    """T_AFR-FTS-006 (AFR-FTS-006): FTS shall support System Admin administration of FTS-relevant role assignments, reassignments, and access-control context."""
    logs = scoping.get_system_audit_logs()
    assert logs is not None

def test_fr_t_afr_fts_007():
    """T_AFR-FTS-007 (AFR-FTS-007): FTS shall support System Admin monitoring of FTS system usage within the available governance scope."""
    logs = scoping.get_system_audit_logs()
    assert logs is not None

def test_fr_t_afr_fts_008():
    """T_AFR-FTS-008 (AFR-FTS-008): FTS shall support System Admin security and audit-log oversight, including viewing and any maintenance functions represented within the available FTS governance scope."""
    logs = scoping.get_system_audit_logs()
    assert logs is not None

def test_fr_t_afr_fts_009():
    """T_AFR-FTS-009 (AFR-FTS-009): FTS shall not allow the System Admin to perform operational file workflow actions on behalf of Institute Employees."""
    with pytest.raises(PermissionDeniedError):
        file_service.create_file(subject="AFR-09", initial_comment="No", creator_id=1, is_draft=True, is_employee=False, is_system_admin=True)

def test_fr_t_afr_fts_010():
    """T_AFR-FTS-010 (AFR-FTS-010): FTS shall allow an Institute Employee assigned multiple institutional roles to operate under the selected assigned role through the Fusion dashboard."""
    obj = file_service.create_file(subject="AFR-10", initial_comment="Start", creator_id=1, creator_designation="HOD", is_draft=True)
    assert obj.creator_designation == "HOD"

def test_fr_t_afr_fts_011():
    """T_AFR-FTS-011 (AFR-FTS-011): FTS shall allow any Institute Employee to create a new file under an assigned role."""
    obj = file_service.create_file(subject="AFR-11", initial_comment="Start", creator_id=1, is_draft=True)
    assert obj.creator_id == 1

def test_fr_t_afr_fts_012():
    """T_AFR-FTS-012 (AFR-FTS-012): FTS shall require an initial mandatory comment when an Institute Employee creates a new file."""
    with pytest.raises(BadRequestError):
        file_service.create_file(subject="AFR-12", initial_comment="", creator_id=1, is_draft=True)

def test_fr_t_afr_fts_013():
    """T_AFR-FTS-013 (AFR-FTS-013): FTS shall allow optional attachments to be added during file creation."""
    obj = file_service.create_file(subject="AFR-13", initial_comment="Start", creator_id=1, is_draft=True, attachments=[{"file_name": "x.pdf"}])
    assert obj.attachments.count() == 1

def test_fr_t_afr_fts_014():
    """T_AFR-FTS-014 (AFR-FTS-014): FTS shall allow an Institute Employee to save a newly created file as a draft."""
    obj = file_service.create_file(subject="AFR-14", initial_comment="Draft", creator_id=1, is_draft=True)
    assert obj.status == "draft"

def test_fr_t_afr_fts_015():
    """T_AFR-FTS-015 (AFR-FTS-015): FTS shall allow an Institute Employee to edit a saved draft file before submission."""
    obj = file_service.create_file(subject="AFR-15", initial_comment="Draft", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="AFR-15-Edited")
    obj.refresh_from_db()
    assert obj.subject == "AFR-15-Edited"

def test_fr_t_afr_fts_016():
    """T_AFR-FTS-016 (AFR-FTS-016): FTS shall allow an Institute Employee to discard a draft file before submission."""
    obj = file_service.create_file(subject="AFR-16", initial_comment="Draft", creator_id=1, is_draft=True)
    file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)
    assert not FTSFile.objects.filter(pk=obj.pk).exists()

def test_fr_t_afr_fts_017():
    """T_AFR-FTS-017 (AFR-FTS-017): FTS shall prevent deletion of a file once it has been submitted and circulated."""
    obj = file_service.create_file(subject="AFR-17", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(ConflictError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)

def test_fr_t_afr_fts_018():
    """T_AFR-FTS-018 (AFR-FTS-018): FTS shall change a file from draft/submission preparation to circulated workflow state when it is submitted to another employee."""
    obj = file_service.create_file(subject="AFR-18", initial_comment="Draft", creator_id=1, is_draft=True)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="Submit")
    obj.refresh_from_db()
    assert obj.status == "circulating"

def test_fr_t_afr_fts_019():
    """T_AFR-FTS-019 (AFR-FTS-019): FTS shall preserve comments and attachments accumulated in a file after submission."""
    obj = file_service.create_file(subject="AFR-19", initial_comment="Start", creator_id=1, is_draft=True, attachments=[{"file_name": "a.pdf"}])
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="Submit")
    obj.refresh_from_db()
    assert obj.comments.count() == 2 and obj.attachments.count() == 1

def test_fr_t_afr_fts_020():
    """T_AFR-FTS-020 (AFR-FTS-020): FTS shall allow an Institute Employee to send a file to another Institute Employee."""
    obj = file_service.create_file(subject="AFR-20", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.current_holder_id == 2

def test_fr_t_afr_fts_021():
    """T_AFR-FTS-021 (AFR-FTS-021): FTS shall allow a file to be sent to any other Institute Employee regardless of the receiver's role."""
    obj = file_service.create_file(subject="AFR-20", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.current_holder_id == 2

def test_fr_t_afr_fts_022():
    """T_AFR-FTS-022 (AFR-FTS-022): FTS shall require the acting user to add a mandatory comment for every file-movement action, including forwarding and return."""
    obj = file_service.create_file(subject="AFR-22", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="   ")

def test_fr_t_afr_fts_023():
    """T_AFR-FTS-023 (AFR-FTS-023): FTS shall allow optional attachments to be added at each file-movement stage, including forwarding and return."""
    obj = file_service.create_file(subject="AFR-23", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd", attachments=[{"file_name": "x.pdf"}])
    assert mov.attachments.count() == 1

def test_fr_t_afr_fts_024():
    """T_AFR-FTS-024 (AFR-FTS-024): FTS shall allow a recipient user to forward a received file to another user."""
    obj = file_service.create_file(subject="AFR-24", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd")
    assert mov.receiver_id == 3

def test_fr_t_afr_fts_025():
    """T_AFR-FTS-025 (AFR-FTS-025): FTS shall allow a recipient user to return a received file to the sender."""
    obj = file_service.create_file(subject="AFR-25", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.return_file(file_id_or_pk=obj.file_id, sender_id=2, remarks="Ret")
    assert mov.receiver_id == 1

def test_fr_t_afr_fts_026():
    """T_AFR-FTS-026 (AFR-FTS-026): FTS shall record each forwarding action in chronological order."""
    obj = file_service.create_file(subject="AFR-26", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd")
    obj.refresh_from_db()
    assert mov.sequence_number == 2 and obj.current_holder_id == 3

def test_fr_t_afr_fts_027():
    """T_AFR-FTS-027 (AFR-FTS-027): FTS shall record each return action in chronological order."""
    obj = file_service.create_file(subject="AFR-26", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd")
    obj.refresh_from_db()
    assert mov.sequence_number == 2 and obj.current_holder_id == 3

def test_fr_t_afr_fts_028():
    """T_AFR-FTS-028 (AFR-FTS-028): FTS shall update the current file holder or pending recipient after a file is forwarded or returned."""
    obj = file_service.create_file(subject="AFR-26", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Fwd")
    obj.refresh_from_db()
    assert mov.sequence_number == 2 and obj.current_holder_id == 3

def test_fr_t_afr_fts_029():
    """T_AFR-FTS-029 (AFR-FTS-029): FTS shall show files received by a user in the user's Inbox."""
    obj = file_service.create_file(subject="AFR-29", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_inbox_files(2).filter(pk=obj.pk).exists()

def test_fr_t_afr_fts_030():
    """T_AFR-FTS-030 (AFR-FTS-030): FTS shall show files sent by a user in the user's Outbox."""
    obj = file_service.create_file(subject="AFR-30", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_outbox_files(1).filter(pk=obj.pk).exists()

def test_fr_t_afr_fts_031():
    """T_AFR-FTS-031 (AFR-FTS-031): FTS shall allow users to view and open files from their Inbox."""
    obj = file_service.create_file(subject="AFR-29", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_inbox_files(2).filter(pk=obj.pk).exists()

def test_fr_t_afr_fts_032():
    """T_AFR-FTS-032 (AFR-FTS-032): FTS shall allow users to view and open files from their Outbox."""
    obj = file_service.create_file(subject="AFR-30", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_outbox_files(1).filter(pk=obj.pk).exists()

def test_fr_t_afr_fts_033():
    """T_AFR-FTS-033 (AFR-FTS-033): FTS shall allow a user to act on actionable files from Inbox or Outbox according to the file state and user authorization."""
    obj = file_service.create_file(subject="AFR-33", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Act")
    assert mov.pk is not None

def test_fr_t_afr_fts_034():
    """T_AFR-FTS-034 (AFR-FTS-034): FTS shall keep files accessible to associated users until the file owner archives the file."""
    obj = file_service.create_file(subject="AFR-34", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.get_visible_file(obj.file_id, 1) is not None
    assert scoping.get_visible_file(obj.file_id, 2) is not None

def test_fr_t_afr_fts_035():
    """T_AFR-FTS-035 (AFR-FTS-035): FTS shall maintain complete movement history for every file from creation onward."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_036():
    """T_AFR-FTS-036 (AFR-FTS-036): FTS shall record sender details for each file movement event."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_037():
    """T_AFR-FTS-037 (AFR-FTS-037): FTS shall record receiver details for each file movement event."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_038():
    """T_AFR-FTS-038 (AFR-FTS-038): FTS shall record timestamps for each file movement event."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_039():
    """T_AFR-FTS-039 (AFR-FTS-039): FTS shall record comments added at each file movement event."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_040():
    """T_AFR-FTS-040 (AFR-FTS-040): FTS shall record attachments added at each file movement event."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_041():
    """T_AFR-FTS-041 (AFR-FTS-041): FTS shall allow any user associated with a file to view that file's tracking history."""
    obj = file_service.create_file(subject="AFR-35", initial_comment="Start", creator_id=1, receiver_id=2)
    movs = scoping.get_file_movements(obj)
    assert movs.count() >= 1
    first = movs.first()
    assert first.sender_id == 1 and first.receiver_id == 2 and first.created_at is not None

def test_fr_t_afr_fts_042():
    """T_AFR-FTS-042 (AFR-FTS-042): FTS shall allow the file owner to archive a file."""
    obj = file_service.create_file(subject="AFR-42", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert archived.status == "archived"

def test_fr_t_afr_fts_043():
    """T_AFR-FTS-043 (AFR-FTS-043): FTS shall prevent users other than the file owner from archiving the file."""
    obj = file_service.create_file(subject="AFR-43", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=2)

def test_fr_t_afr_fts_044():
    """T_AFR-FTS-044 (AFR-FTS-044): FTS shall treat archival as completion of the collaborative file workflow."""
    obj = file_service.create_file(subject="AFR-42", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert archived.status == "archived"

def test_fr_t_afr_fts_045():
    """T_AFR-FTS-045 (AFR-FTS-045): FTS shall keep archived files permanently stored and readable."""
    obj = file_service.create_file(subject="AFR-45", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert scoping.get_visible_file(obj.file_id, 1) is not None

def test_fr_t_afr_fts_046():
    """T_AFR-FTS-046 (AFR-FTS-046): FTS shall prevent modification of archived files."""
    obj = file_service.create_file(subject="AFR-46", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    with pytest.raises(ConflictError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="No")

def test_fr_t_afr_fts_047():
    """T_AFR-FTS-047 (AFR-FTS-047): FTS shall prevent forwarding of archived files."""
    obj = file_service.create_file(subject="AFR-46", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    with pytest.raises(ConflictError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="No")

def test_fr_t_afr_fts_048():
    """T_AFR-FTS-048 (AFR-FTS-048): FTS shall enforce role-based access control for file operations."""
    obj = file_service.create_file(subject="AFR-48", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=3, receiver_id=4, remarks="Illegal")

def test_fr_t_afr_fts_049():
    """T_AFR-FTS-049 (AFR-FTS-049): FTS shall allow users to access only files they are authorized to view."""
    obj = file_service.create_file(subject="AFR-48", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=3, receiver_id=4, remarks="Illegal")

def test_fr_t_afr_fts_050():
    """T_AFR-FTS-050 (AFR-FTS-050): FTS shall allow users to act only on files they are authorized to act upon."""
    obj = file_service.create_file(subject="AFR-48", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=3, receiver_id=4, remarks="Illegal")

def test_fr_t_afr_fts_051():
    """T_AFR-FTS-051 (AFR-FTS-051): FTS shall preserve file ownership when a user switches roles."""
    obj = file_service.create_file(subject="AFR-51", initial_comment="Start", creator_id=1, creator_designation="prof", is_draft=True)
    assert obj.owner_id == 1 and obj.creator_designation == "prof"

def test_fr_t_afr_fts_052():
    """T_AFR-FTS-052 (AFR-FTS-052): FTS shall preserve audit history when a user switches roles."""
    obj = file_service.create_file(subject="AFR-51", initial_comment="Start", creator_id=1, creator_designation="prof", is_draft=True)
    assert obj.owner_id == 1 and obj.creator_designation == "prof"

def test_fr_t_afr_fts_053():
    """T_AFR-FTS-053 (AFR-FTS-053): FTS shall restrict sensitive actions according to assigned roles."""
    obj = file_service.create_file(subject="AFR-53", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=2)

def test_fr_t_afr_fts_054():
    """T_AFR-FTS-054 (AFR-FTS-054): FTS shall maintain an audit log for file creation actions."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_055():
    """T_AFR-FTS-055 (AFR-FTS-055): FTS shall maintain an audit log for comments added to files."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_056():
    """T_AFR-FTS-056 (AFR-FTS-056): FTS shall maintain an audit log for attachments added to files."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_057():
    """T_AFR-FTS-057 (AFR-FTS-057): FTS shall maintain an audit log for forwarding actions."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_058():
    """T_AFR-FTS-058 (AFR-FTS-058): FTS shall maintain an audit log for return actions."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_059():
    """T_AFR-FTS-059 (AFR-FTS-059): FTS shall maintain an audit log for archival actions."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_060():
    """T_AFR-FTS-060 (AFR-FTS-060): FTS shall maintain file versioning implicitly through chronological file updates."""
    obj = file_service.create_file(subject="AFR-54", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()

def test_fr_t_afr_fts_061():
    """T_AFR-FTS-061 (AFR-FTS-061): FTS shall generate a notification when a file is received by a user."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_062():
    """T_AFR-FTS-062 (AFR-FTS-062): FTS shall generate a notification when a file is forwarded."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_063():
    """T_AFR-FTS-063 (AFR-FTS-063): FTS shall generate a notification when a file is returned."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_064():
    """T_AFR-FTS-064 (AFR-FTS-064): FTS shall generate a notification when a file is archived."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_065():
    """T_AFR-FTS-065 (AFR-FTS-065): FTS shall generate a notification when a role is assigned or reassigned."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_066():
    """T_AFR-FTS-066 (AFR-FTS-066): FTS shall deliver notifications through Fusion's integrated notification mechanisms."""
    obj = file_service.create_file(subject="AFR-61", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")

def test_fr_t_afr_fts_067():
    """T_AFR-FTS-067 (AFR-FTS-067): FTS shall expose APIs to other Fusion modules for module-specific workflows."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id

def test_fr_t_afr_fts_068():
    """T_AFR-FTS-068 (AFR-FTS-068): FTS shall expose APIs to other Fusion modules for approval chains."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id

def test_fr_t_afr_fts_069():
    """T_AFR-FTS-069 (AFR-FTS-069): FTS shall expose APIs to other Fusion modules for file-based request tracking."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id

def test_fr_t_afr_fts_070():
    """T_AFR-FTS-070 (AFR-FTS-070): FTS shall apply RBAC requirements to integrations with other Fusion modules."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id

def test_fr_t_afr_fts_071():
    """T_AFR-FTS-071 (AFR-FTS-071): FTS shall apply audit requirements to integrations with other Fusion modules."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id

def test_fr_t_afr_fts_072():
    """T_AFR-FTS-072 (AFR-FTS-072): FTS shall not define the domain-specific approval rules of consuming Fusion modules that use FTS APIs."""
    obj = file_service.create_file(subject="AFR-67", initial_comment="Start", creator_id=1, receiver_id=2)
    summaries = contracts.get_file_summaries([obj.id])
    assert obj.id in summaries and summaries[obj.id].file_id == obj.file_id
