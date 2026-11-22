"""PostgreSQL guards against rewriting immutable HR history."""

from decimal import Decimal

import pytest
from django.db import DatabaseError, transaction
from django.utils import timezone

from modules.hreis import models as hr

pytestmark = pytest.mark.django_db


def _policy():
    return hr.HRPolicyVersion.objects.create(
        family="leave",
        version=1,
        effective_from=timezone.now(),
        parameters={},
        approved_by_user_id=9,
        approved_designation="hradmin",
    )


def _request(policy):
    return hr.HRRequest.objects.create(
        user_id=21,
        family="leave",
        state="approved",
        policy_version=policy,
    )


def _assert_rejects_update_and_delete(model, pk, field, value):
    with pytest.raises(DatabaseError), transaction.atomic():
        model.objects.filter(pk=pk).update(**{field: value})
    assert model.objects.filter(pk=pk).exists()
    with pytest.raises(DatabaseError), transaction.atomic():
        model.objects.filter(pk=pk).delete()
    assert model.objects.filter(pk=pk).exists()


def test_audit_and_policy_version_are_database_immutable():
    # HR-CFR-012, HR-AFR-083, HR-AFR-084, HR-AFR-085,
    # HR-AFR-086, HR-AFR-087, BR-HR-026: append-only historical trail.
    policy = _policy()
    audit = hr.AuditEvent.objects.create(
        event_key="audit-final",
        action="approve",
        resource_kind="leave",
        resource_id=15,
    )
    _assert_rejects_update_and_delete(hr.AuditEvent, audit.pk, "action", "rewritten")
    _assert_rejects_update_and_delete(hr.HRPolicyVersion, policy.pk, "version", 5)


def test_leave_ledger_correction_must_be_a_new_entry():
    policy = _policy()
    request = _request(policy)
    item = hr.LeaveLedgerEntry.objects.create(
        user_id=21,
        leave_type="Casual",
        quantity=Decimal("-2"),
        request=request,
        policy_version=policy,
        event_key="ledger-final",
    )
    _assert_rejects_update_and_delete(hr.LeaveLedgerEntry, item.pk, "quantity", Decimal("-3"))
    reverse = hr.LeaveLedgerEntry.objects.create(
        user_id=21,
        leave_type="Casual",
        quantity=Decimal("2"),
        request=request,
        policy_version=policy,
        reversing=item,
        event_key="ledger-correction",
    )
    assert reverse.pk != item.pk


def test_request_and_service_revision_are_database_immutable():
    policy = _policy()
    request = _request(policy)
    move = hr.HRRequestTransition.objects.create(
        request=request,
        source="pending_authority",
        event="approve",
        target="approved",
        actor_user_id=8,
        acting_designation="HOD (CSE)",
        specification="BW-HR-01",
        step_before=0,
        step_after=0,
        idempotency_key="transition-final",
    )
    _assert_rejects_update_and_delete(hr.HRRequestTransition, move.pk, "target", "rejected")
    record = hr.EmployeeServiceRecord.objects.create(
        user_id=21,
        appointment_details={},
        department="CSE",
        designation_snapshot="Professor",
    )
    revision = hr.ServiceRecordRevision.objects.create(
        record=record,
        revision_number=1,
        snapshot={},
        actor_user_id=8,
        actor_designation="hradmin",
    )
    _assert_rejects_update_and_delete(hr.ServiceRecordRevision, revision.pk, "revision_number", 2)


def test_appraisal_freezes_after_finalization():
    request = hr.HRRequest.objects.create(
        user_id=21,
        family="appraisal",
        state="finalized",
    )
    appraisal = hr.AppraisalDetail.objects.create(
        request=request,
        employee_record=hr.EmployeeServiceRecord.objects.create(
            user_id=21,
            department="CSE",
            designation_snapshot="Synthetic",
        ),
        period_key="2026",
    )
    hr.AppraisalDetail.objects.filter(pk=appraisal.pk).update(
        finalized_at=timezone.now(), archive_reference="approved-reference"
    )
    _assert_rejects_update_and_delete(
        hr.AppraisalDetail, appraisal.pk, "archive_reference", "tampered"
    )
