"""State transition workflow journeys covering all frozen WF cases."""
import pytest

from modules.fts.models import FTSFile
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_wf_bw_fts_01():
    """T_BW-FTS-01: Forward File to Recipient — Zero Onward Traversal."""
    obj = file_service.create_file(subject="BW-01", initial_comment="Start", creator_id=1, receiver_id=2)
    assert obj.status == "circulating" and obj.current_holder_id == 2
    assert obj.movements.count() == 1


def test_wf_bw_fts_02():
    """T_BW-FTS-02: Onward Forwarding — One Loop Traversal."""
    obj = file_service.create_file(subject="BW-02", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Onward")
    obj.refresh_from_db()
    assert obj.status == "circulating" and obj.current_holder_id == 3
    assert obj.movements.count() == 2


def test_wf_bw_fts_03():
    """T_BW-FTS-03: Return File to Previous Sender."""
    obj = file_service.create_file(subject="BW-03", initial_comment="Start", creator_id=1, receiver_id=2)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=2, receiver_id=3, remarks="Onward")
    ret = file_service.return_file(file_id_or_pk=obj.file_id, sender_id=3, remarks="Return")
    obj.refresh_from_db()
    assert ret.receiver_id == 2 and obj.current_holder_id == 2
    assert obj.movements.count() == 3


def test_wf_bw_fts_04():
    """T_BW-FTS-04: Archive Completed Circulated File."""
    obj = file_service.create_file(subject="BW-04", initial_comment="Start", creator_id=1, receiver_id=2)
    archived = file_service.archive_file(file_id_or_pk=obj.file_id, actor_id=1, remarks="Archived")
    assert archived.status == "archived" and archived.movements.count() == 2


def test_wf_bw_fts_05():
    """T_BW-FTS-05: Prepare and Circulate New File — Zero Draft-Edit Traversal."""
    obj = file_service.create_file(subject="BW-05", initial_comment="Initial", creator_id=1, is_draft=True)
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="Circulate")
    obj.refresh_from_db()
    assert obj.status == "circulating" and obj.current_holder_id == 2


def test_wf_bw_fts_06():
    """T_BW-FTS-06: Prepare and Circulate New File — One Draft-Edit Traversal."""
    obj = file_service.create_file(subject="BW-06", initial_comment="Initial", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="BW-06-Edited")
    file_service.forward_file(file_id_or_pk=obj.file_id, sender_id=1, receiver_id=2, remarks="Circulate")
    obj.refresh_from_db()
    assert obj.subject == "BW-06-Edited" and obj.status == "circulating"


def test_wf_bw_fts_07():
    """T_BW-FTS-07: Create and Discard Draft — Zero Draft-Edit Traversal."""
    obj = file_service.create_file(subject="BW-07", initial_comment="Initial", creator_id=1, is_draft=True)
    file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)
    assert not FTSFile.objects.filter(pk=obj.pk).exists()


def test_wf_bw_fts_08():
    """T_BW-FTS-08: Edit Once and Discard Draft — One Draft-Edit Traversal."""
    obj = file_service.create_file(subject="BW-08", initial_comment="Initial", creator_id=1, is_draft=True)
    file_service.edit_draft(file_id_or_pk=obj.file_id, user_id=1, subject="BW-08-Edited")
    file_service.discard_draft(file_id_or_pk=obj.file_id, user_id=1)
    assert not FTSFile.objects.filter(pk=obj.pk).exists()
