"""Batched read-only HR-EIS contract projections for trusted Fusion modules."""

from decimal import Decimal

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from modules.hreis.contracts import (
    get_approved_claim_statuses,
    get_employee_leave_balances,
    get_employee_service_summaries,
    get_request_statuses,
)
from modules.hreis.models import (
    ClaimDetail,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveLedgerEntry,
)

pytestmark = pytest.mark.django_db


def test_read_only_contracts_return_minimal_scoped_fields():
    EmployeeServiceRecord.objects.create(
        user_id=10, department="CSE", designation_snapshot="Professor",
        appointment_details={"private": "not for other modules"},
    )
    EmployeeServiceRecord.objects.create(
        user_id=20, department="ME", designation_snapshot="Lecturer",
        appointment_details={},
    )
    p = HRPolicyVersion.objects.create(
        family="leave", version=1, effective_from=timezone.now(),
        parameters={}, approved_by_user_id=99, approved_designation="hradmin",
    )
    LeaveLedgerEntry.objects.create(
        user_id=10, leave_type="Casual", quantity=Decimal("5"),
        event_key="credit-test", policy_version=p,
    )
    LeaveLedgerEntry.objects.create(
        user_id=10, leave_type="Casual", quantity=Decimal("-2"),
        event_key="debit-test", policy_version=p,
    )
    leave = HRRequest.objects.create(user_id=10, family="leave", state="pending_authority")
    approved = HRRequest.objects.create(
        user_id=20, family="ltc", state="financial_processing_recorded"
    )
    ClaimDetail.objects.create(
        request=approved, claim_type="ltc", subtype="advance",
        financial_processing_details={
            "payment_status": "payment_pending",
            "external_status_reference": "private-reference",
        },
    )

    records = get_employee_service_summaries([10, 100])
    assert list(records) == [10]
    assert records[10].department == "CSE"
    assert "private" not in vars(records[10])
    assert get_employee_leave_balances([10, 20], "Casual") == {
        10: Decimal("3"), 20: Decimal("0"),
    }
    statuses = get_request_statuses([leave.pk, approved.pk, 9999])
    assert statuses[leave.pk].state == "pending_authority"
    assert not hasattr(statuses[leave.pk], "payload")
    approved_claims = get_approved_claim_statuses([leave.pk, approved.pk])
    assert list(approved_claims) == [approved.pk]
    assert approved_claims[approved.pk].externally_reported_payment_status == "payment_pending"
    assert "private-reference" not in repr(approved_claims[approved.pk])


def test_contracts_fail_closed_on_bad_scope_and_invalid_leave_type():
    assert get_employee_service_summaries([None, 0, -7]) == {}
    assert get_employee_leave_balances([], "Casual") == {}
    assert get_request_statuses([]) == {}
    assert get_approved_claim_statuses([]) == {}
    with pytest.raises(ValueError):
        get_employee_leave_balances([10], "Unknown")


def test_contract_list_queries_are_batched():
    for user_id in range(1, 21):
        EmployeeServiceRecord.objects.create(
            user_id=user_id, department="CSE", designation_snapshot="Teacher",
            appointment_details={},
        )
    with CaptureQueriesContext(connection) as q:
        result = get_employee_service_summaries(list(range(1, 21)))
    assert len(result) == 20
    assert len(q) <= 2
