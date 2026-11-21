"""Use case journey checks covering all 22 frozen UC cases."""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.fts.models import FTSFile
from modules.fts.selectors import scoping
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_fts_uc_001_main():
    """T_FTS-UC-001_MAIN: create draft file with initial comment and attachment."""
    obj = file_service.create_file(subject="UC-001-Main", initial_comment="Start note", creator_id=1, is_draft=True, attachments=[{"file_name": "spec.pdf"}])
    assert obj.status == "draft" and obj.comments.count() == 1 and obj.attachments.count() == 1


def test_fts_uc_001_alt1():
    """T_FTS-UC-001_ALT1: immediate circulation upon creation."""
    obj = file_service.create_file(subject="UC-001-Alt1", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.status == "circulating" and obj.current_holder_id == 2


def test_fts_uc_001_alt2():
    """T_FTS-UC-001_ALT2: file creation proceeds without optional attachment."""
    obj = file_service.create_file(subject="UC-001-Alt2", initial_comment="No attachment", creator_id=1, is_draft=True)
    assert obj.attachments.count() == 0


def test_fts_uc_001_alt3():
    """T_FTS-UC-001_ALT3: missing initial comment blocks file creation."""
    with pytest.raises(BadRequestError):
        file_service.create_file(subject="UC-001-Alt3", initial_comment="", creator_id=1, is_draft=True)


def test_fts_uc_001_alt4():
    """T_FTS-UC-001_ALT4: unauthorized role denied file creation."""
    with pytest.raises(PermissionDeniedError):
        file_service.create_file(subject="UC-001-Alt4", initial_comment="Denied", creator_id=1, is_draft=True, is_employee=False, is_system_admin=True)


def test_fts_uc_002_main():
    """T_FTS-UC-002_MAIN: edit draft file subject and comment."""
    obj = file_service.create_file(subject="UC-002-Main", initial_comment="Initial", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="UC-002-Updated", comment="New Note")
    obj.refresh_from_db()
    assert obj.subject == "UC-002-Updated"


def test_fts_uc_002_alt1():
    """T_FTS-UC-002_ALT1: discard pre-circulation draft."""
    obj = file_service.create_file(subject="UC-002-Alt1", initial_comment="To Discard", creator_id=1, is_draft=True)
    file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)
    assert not FTSFile.objects.filter(pk=obj.pk).exists()


def test_fts_uc_002_alt2():
    """T_FTS-UC-002_ALT2: non-creator cannot edit or discard draft."""
    obj = file_service.create_file(subject="UC-002-Alt2", initial_comment="Initial", creator_id=1, is_draft=True)
    with pytest.raises(PermissionDeniedError):
        file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=2, subject="Hacked")
    with pytest.raises(PermissionDeniedError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=2)


def test_fts_uc_003_main():
    """T_FTS-UC-003_MAIN: forward circulating file to employee."""
    obj = file_service.create_file(subject="UC-003-Main", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Forwarding")
    assert mov.sequence_number == 2 and mov.receiver_id == 3


def test_fts_uc_003_alt1():
    """T_FTS-UC-003_ALT1: forwarding without comment blocked."""
    obj = file_service.create_file(subject="UC-003-Alt1", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="   ")


def test_fts_uc_003_alt2():
    """T_FTS-UC-003_ALT2: self-forwarding rejected."""
    obj = file_service.create_file(subject="UC-003-Alt2", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=2, remarks="Self")


def test_fts_uc_003_alt3():
    """T_FTS-UC-003_ALT3: non-holder cannot forward file."""
    obj = file_service.create_file(subject="UC-003-Alt3", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=3, remarks="Not holder")


def test_fts_uc_004_main():
    """T_FTS-UC-004_MAIN: return received file to previous sender."""
    obj = file_service.create_file(subject="UC-004-Main", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.return_file(file_id_or_pk=obj.file_id, sender_id=2, remarks="Returning")
    assert mov.sequence_number == 2 and mov.receiver_id == 1


def test_fts_uc_004_alt1():
    """T_FTS-UC-004_ALT1: return without comment blocked."""
    obj = file_service.create_file(subject="UC-004-Alt1", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.return_file(file_id_or_pk=obj.file_id, sender_id=2, remarks=" ")


def test_fts_uc_004_alt2():
    """T_FTS-UC-004_ALT2: non-holder cannot return file."""
    obj = file_service.create_file(subject="UC-004-Alt2", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.return_file(file_id_or_pk=obj.file_id, sender_id=1, remarks="Not holder")


def test_fts_uc_005_main():
    """T_FTS-UC-005_MAIN: view inbox and outbox lists."""
    obj = file_service.create_file(subject="UC-005-Main", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.visible_inbox_files(user_id=2).filter(pk=obj.pk).exists()
    assert scoping.visible_outbox_files(user_id=1).filter(pk=obj.pk).exists()


def test_fts_uc_005_alt1():
    """T_FTS-UC-005_ALT1: unassociated user cannot access file."""
    obj = file_service.create_file(subject="UC-005-Alt1", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.get_visible_file(obj.file_id, 99) is None


def test_fts_uc_006_main():
    """T_FTS-UC-006_MAIN: view file tracking history."""
    obj = file_service.create_file(subject="UC-006-Main", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Step 2")
    history = scoping.get_file_movements(obj)
    assert len(history) == 2


def test_fts_uc_007_main():
    """T_FTS-UC-007_MAIN: owner archives completed file."""
    obj = file_service.create_file(subject="UC-007-Main", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1, remarks="Archiving")
    assert archived.status == "archived"


def test_fts_uc_007_alt1():
    """T_FTS-UC-007_ALT1: non-owner archival attempt denied."""
    obj = file_service.create_file(subject="UC-007-Alt1", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=2)


def test_fts_uc_007_alt2():
    """T_FTS-UC-007_ALT2: archived file is read-only and rejects forwarding."""
    obj = file_service.create_file(subject="UC-007-Alt2", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    with pytest.raises(ConflictError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=3, remarks="Denied")


def test_fts_uc_008_main():
    """T_FTS-UC-008_MAIN: select assigned role context for FTS operations."""
    obj = file_service.create_file(subject="UC-008-Main", initial_comment="Start", creator_id=10, creator_designation="HOD", is_draft=True)
    assert obj.owner_id == 10 and obj.creator_designation == "HOD"
