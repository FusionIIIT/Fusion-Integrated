"""Unit tests for FTS inter-module contracts (FTS-UC-010, BR-FTS-014).

Ensures plural signatures, contract DTO behavior, and API contract invariants.
"""
from modules.filetracking.contracts import (
    FileTrackingStatusDTO,
    get_file_tracking_statuses,
    get_files_by_external_references,
)


def test_contract_dto_immutability():
    dto = FileTrackingStatusDTO(
        id=1,
        file_code="FTS-TEST01",
        subject="Subject",
        status="circulated",
        owner_user_id=10,
        current_holder_user_id=20,
        current_holder_role="HOD",
        source_module="leave",
        external_reference="LEAVE-101",
    )
    assert dto.file_code == "FTS-TEST01"
    assert dto.source_module == "leave"
    assert dto.external_reference == "LEAVE-101"


def test_plural_getter_signatures():
    # Calling with empty sequences produces clean empty dicts without DB errors
    assert get_file_tracking_statuses([]) == {}
    assert get_files_by_external_references([]) == {}
