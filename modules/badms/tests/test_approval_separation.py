from datetime import date
from types import SimpleNamespace

import pytest

from core.api.exceptions import NotFoundError
from modules.badms.models import ArchiveRequest, RestorationRequest, StorageExtensionRequest
from modules.badms.services import archives, restorations, storage_extensions

pytestmark = pytest.mark.django_db


def make_archive(*, status="Submitted", classification="Routine"):
    return ArchiveRequest.objects.create(
        user_id=4101,
        department="CSE",
        requester_email="student@example.test",
        file_name="data.zip",
        file_date=date(2026, 11, 20),
        owners=["Student"],
        file_type="application/zip",
        reason="Test record",
        attachment_key="incoming/data.zip",
        attachment_size_bytes=100,
        status=status,
        classification=classification,
    )


def test_submitter_cannot_decide_or_classify_own_archive():
    actor = SimpleNamespace(user_id=4101)
    submitted = make_archive()
    classified = make_archive(status="HoD Approved")

    with pytest.raises(NotFoundError):
        archives.decide(request_id=submitted.pk, actor=actor, department="CSE", approve=True)
    with pytest.raises(NotFoundError):
        archives.classify(request_id=classified.pk, actor=actor, classification="Sensitive")


def test_submitter_cannot_handle_own_sensitive_archive():
    actor = SimpleNamespace(user_id=4101)
    row = make_archive(
        status="Classified Sensitive / Routed to IT Security", classification="Sensitive"
    )

    with pytest.raises(NotFoundError):
        archives.create_sensitive_archive(request_id=row.pk, actor=actor)


def test_submitter_cannot_decide_own_storage_extension():
    actor = SimpleNamespace(user_id=4101)
    request = StorageExtensionRequest.objects.create(
        user_id=4101,
        department="CSE",
        requester_email="student@example.test",
        requested_bytes=100,
        justification="Need storage",
        usage_bytes=100,
        available_bytes=1000,
    )

    with pytest.raises(NotFoundError):
        storage_extensions.decide(
            request_id=request.pk, actor=actor, department="CSE", approve=True, note=""
        )


def test_restoration_requester_cannot_approve_or_execute_own_restoration():
    actor = SimpleNamespace(user_id=4101)
    archive = make_archive(status="Sensitive Archive Encrypted", classification="Sensitive")
    pending = RestorationRequest.objects.create(
        user_id=4101,
        department="CSE",
        requester_email="student@example.test",
        archive_request=archive,
        classification="Sensitive",
        status="Sensitive Restoration Pending Approval",
    )
    approved = RestorationRequest.objects.create(
        user_id=4101,
        department="CSE",
        requester_email="student@example.test",
        archive_request=archive,
        classification="Sensitive",
        status="Approved for Restoration",
    )

    with pytest.raises(NotFoundError):
        restorations.decide_sensitive(request_id=pending.pk, actor=actor, approve=True)
    with pytest.raises(NotFoundError):
        restorations.execute_restore(request_id=approved.pk, actor=actor)
