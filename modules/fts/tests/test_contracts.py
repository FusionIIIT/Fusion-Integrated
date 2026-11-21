"""Contract tests for FTS cross-module surface."""
import pytest

from modules.fts import contracts
from modules.fts.services import file_service

pytestmark = pytest.mark.django_db


def test_get_file_summaries_plural():
    f1 = file_service.create_file(
        subject="Summary File 1",
        initial_comment="Note 1.",
        creator_id=101,
        receiver_id=102,
    )
    f2 = file_service.create_file(
        subject="Summary File 2",
        initial_comment="Note 2.",
        creator_id=101,
        is_draft=True,
    )

    summaries = contracts.get_file_summaries([f1.id, f2.id, 99999])
    assert len(summaries) == 2
    assert summaries[f1.id].status == "circulating"
    assert summaries[f1.id].current_holder_id == 102
    assert summaries[f2.id].status == "draft"
    assert summaries[f2.id].current_holder_id == 101


def test_get_file_summaries_by_code():
    f1 = file_service.create_file(
        subject="Code File 1",
        initial_comment="Init.",
        creator_id=101,
        receiver_id=102,
    )

    summaries = contracts.get_file_summaries_by_code([f1.file_id, "NONEXISTENT"])
    assert len(summaries) == 1
    assert summaries[f1.file_id].subject == "Code File 1"
