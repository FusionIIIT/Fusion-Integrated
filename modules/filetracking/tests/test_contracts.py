"""Unit tests for File Tracking System public contracts."""

import pytest

from modules.filetracking.contracts import (
    get_file_statuses,
    get_files_for_holders,
    initiate_module_tracking_chain,
)
from modules.filetracking.services import create_file


@pytest.mark.django_db
def test_contracts_plural_getters():
    f1 = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Module Tracking A",
        initial_comment="Tracking chain A",
        is_draft=False,
        recipient_user_id=2,
    )
    f2 = create_file(
        creator_user_id=1,
        creator_designation="faculty",
        subject="Module Tracking B",
        initial_comment="Tracking chain B",
        is_draft=False,
        recipient_user_id=3,
    )

    statuses = get_file_statuses([f1.id, f2.id])
    assert len(statuses) == 2
    assert {s.file_id for s in statuses} == {f1.id, f2.id}
    assert get_file_statuses([]) == []

    holder_files = get_files_for_holders([2])
    assert len(holder_files) == 1
    assert holder_files[0].file_id == f1.id
    assert get_files_for_holders([]) == []


@pytest.mark.django_db
def test_initiate_module_tracking_chain():
    dto = initiate_module_tracking_chain(
        initiator_user_id=1,
        initiator_designation="Purchase Officer",
        subject="Purchase Request PR-1002",
        initial_comment="PO initiated file",
        recipient_user_id=2,
        recipient_designation="Finance Officer",
    )
    assert dto.file_id > 0
    assert dto.status == "circulating"
    assert dto.current_holder_user_id == 2
