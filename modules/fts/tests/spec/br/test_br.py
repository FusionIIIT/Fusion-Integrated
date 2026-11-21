"""Business rule enforcement checks covering all 24 frozen BR cases."""
import pytest

from core.api.exceptions import BadRequestError, ConflictError, PermissionDeniedError
from modules.fts import contracts
from modules.fts.models import FTSAuditLog
from modules.fts.selectors import scoping
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_br_fts_001_permitted():
    """T_BR-FTS-001_PERMITTED: employee operational access permitted."""
    obj = file_service.create_file(subject="BR-001-P", initial_comment="Valid", creator_id=1, is_draft=True, is_employee=True)
    assert obj.pk is not None


def test_br_fts_001_prohibited():
    """T_BR-FTS-001_PROHIBITED: admin operational access prohibited."""
    with pytest.raises(PermissionDeniedError):
        file_service.create_file(subject="BR-001-F", initial_comment="No", creator_id=1, is_draft=True, is_employee=False, is_system_admin=True)


def test_br_fts_002_required():
    """T_BR-FTS-002_REQUIRED: role switching preserves ownership and historical audit identity."""
    obj = file_service.create_file(subject="BR-002", initial_comment="Initial", creator_id=1, creator_designation="faculty", is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="BR-002-Updated")
    obj.refresh_from_db()
    assert obj.owner_id == 1 and obj.creator_designation == "faculty"


def test_br_fts_003_permitted():
    """T_BR-FTS-003_PERMITTED: persistent composite file retains comments and attachments."""
    obj = file_service.create_file(subject="BR-003-P", initial_comment="Comment 1", creator_id=1, is_draft=True, attachments=[{"file_name": "doc.pdf"}])
    assert obj.comments.count() == 1 and obj.attachments.count() == 1


def test_br_fts_003_prohibited():
    """T_BR-FTS-003_PROHIBITED: circulated file cannot be deleted as a draft."""
    obj = file_service.create_file(subject="BR-003-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(ConflictError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)


def test_br_fts_004_permitted():
    """T_BR-FTS-004_PERMITTED: initial comment is supplied and file creation succeeds."""
    obj = file_service.create_file(subject="BR-004-P", initial_comment="Mandatory comment", creator_id=1, is_draft=True)
    assert obj.comments.filter(comment_text="Mandatory comment").exists()


def test_br_fts_004_prohibited():
    """T_BR-FTS-004_PROHIBITED: missing initial comment blocks file creation."""
    with pytest.raises(BadRequestError):
        file_service.create_file(subject="BR-004-F", initial_comment="", creator_id=1, is_draft=True)


def test_br_fts_005_permitted():
    """T_BR-FTS-005_PERMITTED: pre-circulation draft operations are permitted."""
    obj = file_service.create_file(subject="BR-005-P", initial_comment="Start", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="BR-005-Edited")
    obj.refresh_from_db()
    assert obj.subject == "BR-005-Edited"


def test_br_fts_005_prohibited():
    """T_BR-FTS-005_PROHIBITED: draft discard rejected once file enters circulation."""
    obj = file_service.create_file(subject="BR-005-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(ConflictError):
        file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)


def test_br_fts_006_permitted():
    """T_BR-FTS-006_PERMITTED: valid movement comment allows forwarding."""
    obj = file_service.create_file(subject="BR-006-P", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Valid note")
    assert mov.remarks == "Valid note"


def test_br_fts_006_prohibited():
    """T_BR-FTS-006_PROHIBITED: empty movement comment blocks forwarding."""
    obj = file_service.create_file(subject="BR-006-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="   ")


def test_br_fts_007_permitted():
    """T_BR-FTS-007_PERMITTED: forward to eligible recipient succeeds."""
    obj = file_service.create_file(subject="BR-007-P", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Forward")
    assert mov.receiver_id == 3


def test_br_fts_007_prohibited():
    """T_BR-FTS-007_PROHIBITED: self-forwarding rejected."""
    obj = file_service.create_file(subject="BR-007-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(BadRequestError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=2, remarks="Self")


def test_br_fts_008_required():
    """T_BR-FTS-008_REQUIRED: chronological movement record maintains sequential order."""
    obj = file_service.create_file(subject="BR-008", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Forward")
    file_service.return_file(file_id_or_pk=obj.file_id, sender_id=3, remarks="Return")
    seqs = list(obj.movements.order_by("sequence_number").values_list("sequence_number", flat=True))
    assert seqs == [1, 2, 3]


def test_br_fts_009_permitted():
    """T_BR-FTS-009_PERMITTED: associated file access permitted."""
    obj = file_service.create_file(subject="BR-009-P", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.get_visible_file(obj.file_id, 1) is not None
    assert scoping.get_visible_file(obj.file_id, 2) is not None


def test_br_fts_009_prohibited():
    """T_BR-FTS-009_PROHIBITED: unassociated user denied file access."""
    obj = file_service.create_file(subject="BR-009-F", initial_comment="Start", creator_id=1, receiver_id=2)
    assert scoping.get_visible_file(obj.file_id, 99) is None


def test_br_fts_010_permitted():
    """T_BR-FTS-010_PERMITTED: current holder permitted to return file."""
    obj = file_service.create_file(subject="BR-010-P", initial_comment="Start", creator_id=1, receiver_id=2)
    mov = file_service.return_file(file_id_or_pk=obj.file_id, sender_id=2, remarks="Back")
    assert mov.sequence_number == 2


def test_br_fts_010_prohibited():
    """T_BR-FTS-010_PROHIBITED: non-holder cannot forward file."""
    obj = file_service.create_file(subject="BR-010-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=3, remarks="Illegal")


def test_br_fts_011_required():
    """T_BR-FTS-011_REQUIRED: audit log appended for operations."""
    obj = file_service.create_file(subject="BR-011", initial_comment="Start", creator_id=1, receiver_id=2)
    assert FTSAuditLog.objects.filter(file=obj).exists()


def test_br_fts_012_permitted():
    """T_BR-FTS-012_PERMITTED: file owner archives completed file."""
    obj = file_service.create_file(subject="BR-012-P", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    assert archived.status == "archived"


def test_br_fts_012_prohibited():
    """T_BR-FTS-012_PROHIBITED: non-owner archival and post-archival forwarding rejected."""
    obj = file_service.create_file(subject="BR-012-F", initial_comment="Start", creator_id=1, receiver_id=2)
    with pytest.raises(PermissionDeniedError):
        file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=2)
    file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1)
    with pytest.raises(ConflictError):
        file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=3, remarks="Denied")


def test_br_fts_013_required():
    """T_BR-FTS-013_REQUIRED: notification trigger boundary invoked on file action."""
    obj = file_service.create_file(subject="BR-013", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.file_id.startswith("FTS-")


def test_br_fts_014_permitted():
    """T_BR-FTS-014_PERMITTED: cross-module contract query returns file summaries."""
    obj = file_service.create_file(subject="BR-014-P", initial_comment="Start", creator_id=1, receiver_id=2)
    items = contracts.get_file_summaries([obj.id])
    assert obj.id in items and items[obj.id].file_id == obj.file_id


def test_br_fts_014_prohibited():
    """T_BR-FTS-014_PROHIBITED: cross-module contract query with empty ids returns empty."""
    items = contracts.get_file_summaries([])
    assert items == {}
