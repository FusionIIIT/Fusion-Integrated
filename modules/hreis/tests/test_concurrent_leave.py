"""Cross-request balance spending is serialized across independent DB sessions."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal
from threading import Barrier

import pytest
from django.db import close_old_connections
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.hreis.models import (
    ApprovalRouteStep,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    LeaveLedgerEntry,
)
from modules.hreis.services.transitions import decide_request
from modules.hreis.tests.actors import Principal

pytestmark = pytest.mark.django_db(transaction=True)


def test_parallel_leave_final_approvals_cannot_spend_same_balance_twice():
    # HR-AFR-039, HR-AFR-042, BR-HR-008, BR-HR-010:
    # real concurrent transactions against separate HRRequest rows must
    # serialize on one employee record before either credits a leave debit.
    now = timezone.now()
    policy = HRPolicyVersion.objects.create(
        family="leave",
        version=1,
        effective_from=now - timedelta(days=1),
        effective_until=now + timedelta(days=1),
        parameters={
            "eligibility": {"faculty": {"Casual": True}},
            "routes": [
                {
                    "employee_kind": "faculty",
                    "department": "CSE",
                    "authorities": ["Registrar"],
                }
            ],
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Professor",
        appointment_details={},
        service_history=[],
    )
    LeaveLedgerEntry.objects.create(
        user_id=10,
        leave_type="Casual",
        quantity=Decimal("3"),
        policy_version=policy,
        event_key="concurrent-opening-credit",
    )
    requests = []
    for _ in range(2):
        row = HRRequest.objects.create(
            user_id=10,
            family="leave",
            subtype="Casual",
            state="pending_authority",
            route_step=0,
            policy_version=policy,
            payload={"duration": "2.0000"},
        )
        ApprovalRouteStep.objects.create(
            request=row,
            position=0,
            designation="Registrar",
            policy_version_label="leave:1",
        )
        requests.append(row.pk)
    actor = Principal(
        user_id=201,
        username="registrar",
        display_name="Registrar",
        kind="staff",
        active_role="Registrar",
        roles=("Registrar",),
        permissions=frozenset({"hreis.leave.approve"}),
        modules=("hreis",),
    )
    gate = Barrier(2)

    def decide(request_id):
        close_old_connections()
        try:
            gate.wait(timeout=20)
            return decide_request(
                actor,
                request_id=request_id,
                event="approve",
                reason="",
                idempotency_key=f"concurrent-leave-approval-{request_id}",
            )
        except ConflictError as exc:
            return exc
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(decide, requests))

    assert [getattr(row, "state", None) for row in results].count("approved") == 1
    refused = [row for row in results if isinstance(row, ConflictError)]
    assert len(refused) == 1 and refused[0].code == "insufficient_balance"
    assert HRRequest.objects.filter(pk__in=requests, state="approved").count() == 1
    assert (
        HRRequest.objects.filter(
            pk__in=requests,
            state="pending_authority",
        ).count()
        == 1
    )
    quantities = list(
        LeaveLedgerEntry.objects.filter(user_id=10, leave_type="Casual").values_list(
            "quantity", flat=True
        )
    )
    assert sorted(quantities) == [Decimal("-2"), Decimal("3")]
    assert sum(quantities) == Decimal("1")
