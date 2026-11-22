"""Database constraints for HR-EIS-owned business data only."""

from datetime import timedelta
from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.db.models import ForeignKey, OneToOneField
from django.utils import timezone

from modules.hreis import models as hr

pytestmark = pytest.mark.django_db


@pytest.fixture
def policy():
    return hr.HRPolicyVersion.objects.create(
        family="leave",
        version=1,
        effective_from=timezone.now() - timedelta(days=1),
        parameters={"eligibility": "configured_for_test_only"},
        approved_by_user_id=12,
        approved_designation="hradmin",
    )


@pytest.fixture
def hr_request(policy):
    return hr.HRRequest.objects.create(
        user_id=17,
        family="leave",
        state="pending_authority",
        subtype="Casual",
        policy_version=policy,
    )


def _record(user_id):
    return hr.EmployeeServiceRecord.objects.create(
        user_id=user_id,
        appointment_details={"date": "2026-01-01"},
        department="CSE",
        designation_snapshot="Assistant Professor",
    )


def test_one_service_record_per_employee_and_sequential_revisions():
    record = _record(1)
    hr.ServiceRecordRevision.objects.create(
        record=record,
        revision_number=1,
        snapshot={"department": "CSE"},
        actor_user_id=8,
        actor_designation="hradmin",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        _record(1)
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.ServiceRecordRevision.objects.create(
            record=record,
            revision_number=1,
            snapshot={"department": "ME"},
            actor_user_id=8,
            actor_designation="hradmin",
        )


def test_policy_versions_are_unique_and_interval_valid(policy):
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.HRPolicyVersion.objects.create(
            family="leave",
            version=1,
            effective_from=timezone.now(),
            parameters={},
            approved_by_user_id=12,
            approved_designation="hradmin",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.HRPolicyVersion.objects.create(
            family="cpda",
            version=1,
            effective_from=timezone.now(),
            effective_until=timezone.now() - timedelta(days=1),
            parameters={},
            approved_by_user_id=12,
            approved_designation="hradmin",
        )


def test_request_family_cannot_escape_declared_four(policy):
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.HRRequest.objects.create(
            user_id=17,
            family="payroll",
            state="draft",
            policy_version=policy,
        )


def test_route_step_unique_and_actor_is_an_iam_designation_string(hr_request):
    hr.ApprovalRouteStep.objects.create(
        request=hr_request,
        position=0,
        designation="HOD (CSE)",
        policy_version_label="leave-1",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.ApprovalRouteStep.objects.create(
            request=hr_request,
            position=0,
            designation="Director",
            policy_version_label="leave-1",
        )


def test_leave_ledger_forbids_zero_and_duplicate_charge(policy, hr_request):
    item = hr.LeaveLedgerEntry.objects.create(
        user_id=17,
        leave_type="Casual",
        quantity=Decimal("-1.0000"),
        policy_version=policy,
        request=hr_request,
        event_key="leave-approved-1",
    )
    assert item.user_id == hr_request.user_id
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.LeaveLedgerEntry.objects.create(
            user_id=17,
            leave_type="Casual",
            quantity=Decimal("0"),
            policy_version=policy,
            event_key="zero-entry",
        )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.LeaveLedgerEntry.objects.create(
            user_id=17,
            leave_type="Casual",
            quantity=Decimal("-1"),
            policy_version=policy,
            event_key="leave-approved-1",
        )


def test_one_reversal_of_a_leave_ledger_event(policy, hr_request):
    charge = hr.LeaveLedgerEntry.objects.create(
        user_id=17,
        leave_type="Casual",
        quantity=Decimal("-1"),
        policy_version=policy,
        request=hr_request,
        event_key="event-charge",
    )
    hr.LeaveLedgerEntry.objects.create(
        user_id=17,
        leave_type="Casual",
        quantity=Decimal("1"),
        policy_version=policy,
        request=hr_request,
        event_key="event-reverse",
        reversing=charge,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.LeaveLedgerEntry.objects.create(
            user_id=17,
            leave_type="Casual",
            quantity=Decimal("1"),
            policy_version=policy,
            request=hr_request,
            event_key="duplicate-reversal",
            reversing=charge,
        )


def test_cpda_claim_amount_cannot_be_nonpositive(hr_request):
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.ClaimDetail.objects.create(
            request=hr_request,
            claim_type="cpda",
            subtype="advance",
            purpose="Research",
            amount=Decimal("-0.01"),
        )


def test_audit_outbox_notification_and_transition_keys_are_unique(hr_request):
    hr.AuditEvent.objects.create(
        event_key="audit-1",
        actor_user_id=8,
        action="submit",
        resource_kind="request",
        resource_id=hr_request.id,
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.AuditEvent.objects.create(
            event_key="audit-1",
            action="repeat",
            resource_kind="request",
            resource_id=hr_request.id,
        )
    hr.OutboxEvent.objects.create(event_key="outbox-1", event_type="request_submitted")
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.OutboxEvent.objects.create(event_key="outbox-1", event_type="repeat")
    hr.Notification.objects.create(
        recipient_user_id=17,
        request=hr_request,
        event_key="notification-1",
        title="Submitted",
        message="Your request was submitted.",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.Notification.objects.create(
            recipient_user_id=17,
            request=hr_request,
            event_key="notification-1",
            title="Repeat",
            message="Duplicate",
        )
    hr.HRRequestTransition.objects.create(
        request=hr_request,
        source="draft",
        event="submit",
        target="pending_authority",
        actor_user_id=17,
        acting_designation="faculty",
        specification="CW-HR-01",
        step_before=0,
        step_after=0,
        idempotency_key="transition-1",
    )
    with pytest.raises(IntegrityError), transaction.atomic():
        hr.HRRequestTransition.objects.create(
            request=hr_request,
            source="draft",
            event="submit",
            target="pending_authority",
            actor_user_id=17,
            acting_designation="faculty",
            specification="CW-HR-01",
            step_before=0,
            step_after=0,
            idempotency_key="transition-1",
        )


def test_no_model_foreign_key_crosses_module_boundary():
    for model in (
        hr.AppraisalDetail,
        hr.ApprovalRouteStep,
        hr.AuditEvent,
        hr.ClaimDetail,
        hr.ClaimDocument,
        hr.EmployeeServiceRecord,
        hr.HRPolicyVersion,
        hr.HRRequest,
        hr.HRRequestTransition,
        hr.LeaveLedgerEntry,
        hr.Notification,
        hr.OutboxEvent,
        hr.ServiceRecordRevision,
    ):
        for field in model._meta.fields:
            if isinstance(field, (ForeignKey, OneToOneField)):
                assert field.remote_field.model._meta.app_label == "hreis"


def test_payroll_and_salary_structures_are_outside_hr_eis_write_scope():
    # HR-CFR-014, HR-AFR-104, HR-AFR-105, BR-HR-031:
    # no payroll/salary family, write permission, or owned mutable table.
    from django.apps import apps

    from modules.hreis.domain.workflow import FAMILIES
    from modules.hreis.registry import PERMISSIONS

    assert set(FAMILIES) == {"leave", "appraisal", "ltc", "cpda"}
    assert all("payroll" not in code and "salary" not in code for code, _description in PERMISSIONS)
    assert all(
        model._meta.db_table.startswith("hreis_")
        for model in apps.get_app_config("hreis").get_models()
    )


def test_iam_role_assignment_and_reassignment_are_not_hr_eis_write_actions():
    # HR-AFR-096, HR-AFR-097, BR-HR-029:
    # HR-EIS consumes signed active-role/permissions from Fusion, never issues
    # role assignment or role-change commands itself.
    from modules.hreis.api.urls import urlpatterns
    from modules.hreis.registry import PERMISSIONS, ROLE_GRANTS

    codes = {code for code, _description in PERMISSIONS}
    assert not any(code.startswith(("hreis.role.", "hreis.designation.")) for code in codes)
    assert not any(
        "assign-role" in (route.name or "") or "reassign-role" in (route.name or "")
        for route in urlpatterns
    )
    assert "faculty" in ROLE_GRANTS and "hradmin" in ROLE_GRANTS
