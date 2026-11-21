"""Transactional HR master-data operations: role gates and rollback."""

from types import SimpleNamespace

import pytest

from core.api.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from fusion_auth.principal import Principal
from modules.hreis.models import AuditEvent, EmployeeServiceRecord, ServiceRecordRevision
from modules.hreis.services import records

pytestmark = pytest.mark.django_db


def _actor(
    role="hradmin",
    permissions=("hreis.service_record.create", "hreis.service_record.update"),
    modules=("hreis",),
):
    return Principal(
        user_id=99,
        username="hradmin",
        display_name="HR admin",
        kind="staff",
        active_role=role,
        roles=("hradmin", "staff"),
        permissions=frozenset(permissions),
        modules=modules,
    )


@pytest.fixture(autouse=True)
def fake_directory(monkeypatch):
    def lookup(ids):
        return {i: SimpleNamespace(kind="faculty") for i in ids if i == 10}

    monkeypatch.setattr(records, "get_users", lookup)


@pytest.fixture
def new_fields():
    return {
        "appointment_details": {"joined_on": "2026-11-20"},
        "department": "CSE",
        "designation_snapshot": "Assistant Professor",
        "service_history": [],
        "retirement_status": "",
    }


def _create(fields, key="create-1"):
    return records.create_record(
        _actor(),
        user_id=10,
        fields=fields,
        idempotency_key=key,
    )


def test_creation_is_atomic_and_audited_with_revision(new_fields):
    # HR-CFR-006, HR-AFR-019, HR-AFR-020, HR-AFR-021,
    # HR-AFR-022, HR-AFR-023, HR-AFR-025, BR-HR-004:
    # official record fields, first immutable revision and actor audit.
    row = _create(new_fields)
    assert row.revision == 1
    revision = ServiceRecordRevision.objects.get(record=row, revision_number=1)
    assert revision.snapshot["department"] == "CSE"
    audit = AuditEvent.objects.get(event_key="service:create-1")
    assert audit.actor_user_id == 99
    assert audit.acting_designation == "hradmin"
    assert "appointment_details" in audit.data["changed_fields"]
    assert "joined_on" not in audit.data


def test_update_increments_revision_without_rewriting_history(new_fields):
    # HR-AFR-027, HR-AFR-102, BR-HR-005, BR-HR-006:
    # updates append a new snapshot rather than rewriting the prior revision.
    row = _create(new_fields)
    updated = records.update_record(
        _actor(),
        record_id=row.pk,
        expected_revision=1,
        fields={"department": "ME"},
        idempotency_key="update-1",
    )
    assert updated.revision == 2
    assert updated.department == "ME"
    assert list(
        ServiceRecordRevision.objects.filter(record=row)
        .order_by("revision_number")
        .values_list(
            "revision_number",
            flat=True,
        )
    ) == [1, 2]
    assert (
        ServiceRecordRevision.objects.get(
            record=row,
            revision_number=1,
        ).snapshot["department"]
        == "CSE"
    )
    assert AuditEvent.objects.filter(resource_kind="service_record").count() == 2


def test_replay_and_stale_revision_do_not_mutate(new_fields):
    # HR-AFR-102, HR-AFR-103, BR-HR-006: stale/replayed updates fail closed.
    row = _create(new_fields)
    with pytest.raises(ConflictError) as exc:
        _create(new_fields)
    assert exc.value.code in {"operation_replayed", "record_exists"}
    with pytest.raises(ConflictError) as exc:
        records.update_record(
            _actor(),
            record_id=row.pk,
            expected_revision=0,
            fields={"department": "Design"},
            idempotency_key="update-1",
        )
    assert exc.value.code == "stale_record_revision"
    assert EmployeeServiceRecord.objects.get(pk=row.pk).department == "CSE"
    assert ServiceRecordRevision.objects.filter(record=row).count() == 1


def test_role_must_be_current_hradmin_not_just_held(new_fields):
    # HR-AFR-095, HR-AFR-101, HR-AFR-107, BR-HR-005:
    # the acting role, not an unrelated held grant, must own the update.
    with pytest.raises(PermissionDeniedError):
        records.create_record(
            _actor(role="staff"),
            user_id=10,
            fields=new_fields,
            idempotency_key="wrong-active-role",
        )
    with pytest.raises(PermissionDeniedError):
        records.create_record(
            _actor(permissions=()),
            user_id=10,
            fields=new_fields,
            idempotency_key="no-create-grant",
        )
    with pytest.raises(PermissionDeniedError):
        records.create_record(
            _actor(modules=()),
            user_id=10,
            fields=new_fields,
            idempotency_key="no-module-grant",
        )
    assert not EmployeeServiceRecord.objects.exists()


def test_user_identity_never_written_without_directory_evidence(new_fields):
    # BR-HR-001, BR-HR-028: directory identity must exist; HR-EIS is not IAM.
    with pytest.raises(NotFoundError):
        records.create_record(
            _actor(),
            user_id=999,
            fields=new_fields,
            idempotency_key="unknown-user",
        )
    assert not EmployeeServiceRecord.objects.exists()


@pytest.mark.parametrize(
    "fields",
    [
        {"user_id": 100},
        {"designation_snapshot": ""},
        {"department": ""},
        {"department": 123},
        {"appointment_details": []},
    ],
)
def test_service_record_input_invalid_and_rejected(new_fields, fields):
    merged = {**new_fields, **fields}
    with pytest.raises(BadRequestError):
        _create(merged)
    assert not EmployeeServiceRecord.objects.exists()


def test_unknown_record_update_is_not_found():
    with pytest.raises(NotFoundError):
        records.update_record(
            _actor(),
            record_id=12345,
            expected_revision=0,
            fields={"department": "ME"},
            idempotency_key="update-missing",
        )


def test_duplicate_idempotency_does_not_duplicate_revisions(new_fields):
    row = _create(new_fields)
    records.update_record(
        _actor(),
        record_id=row.pk,
        expected_revision=1,
        fields={"department": "ME"},
        idempotency_key="update-1",
    )
    with pytest.raises(ConflictError) as exc:
        records.update_record(
            _actor(),
            record_id=row.pk,
            expected_revision=2,
            fields={"department": "Design"},
            idempotency_key="update-1",
        )
    assert exc.value.code == "operation_replayed"
    assert ServiceRecordRevision.objects.filter(record=row).count() == 2


def test_failure_during_audit_rolls_back_record_and_revision(new_fields, monkeypatch):
    # HR-AFR-103, BR-HR-006: a failure cannot partially create official records.
    def broken_audit(*args, **kwargs):
        raise RuntimeError("Synthetic audit storage failure")

    monkeypatch.setattr(records, "_audit", broken_audit)
    with pytest.raises(RuntimeError, match="audit storage failure"):
        _create(new_fields)
    assert not EmployeeServiceRecord.objects.exists()
    assert not ServiceRecordRevision.objects.exists()


def test_hr_administrator_cannot_create_or_mutate_own_official_service_record(new_fields):
    # HR-AFR-026/027/098: segregation applies even to a privileged HR operator.
    with pytest.raises(NotFoundError) as denied_create:
        records.create_record(
            _actor(),
            user_id=99,
            fields=new_fields,
            idempotency_key="self-create-service",
        )
    assert denied_create.value.code == "service_record_not_assigned"
    assert not EmployeeServiceRecord.objects.exists()

    own = EmployeeServiceRecord.objects.create(
        user_id=99, appointment_details={}, department="CSE",
        designation_snapshot="HR administrator", service_history=[],
        revision=1,
    )
    with pytest.raises(NotFoundError) as denied_update:
        records.update_record(
            _actor(),
            record_id=own.pk,
            fields={"designation_snapshot": "Director"},
            expected_revision=1,
            idempotency_key="self-update-service",
        )
    assert denied_update.value.code == "service_record_not_assigned"
    own.refresh_from_db()
    assert own.designation_snapshot == "HR administrator" and own.revision == 1
    assert not AuditEvent.objects.exists()
    assert not ServiceRecordRevision.objects.exists()
