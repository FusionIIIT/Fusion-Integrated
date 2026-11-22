"""Concurrent submissions cannot create a second appraisal for one employee/period."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from time import sleep

import pytest
from django.db import IntegrityError, close_old_connections, transaction
from django.utils import timezone

from core.api.exceptions import ConflictError
from modules.hreis.models import (
    AppraisalDetail,
    AuditEvent,
    EmployeeServiceRecord,
    HRPolicyVersion,
    HRRequest,
    Notification,
    OutboxEvent,
)
from modules.hreis.services import requests as service
from modules.hreis.tests.actors import Principal

pytestmark = pytest.mark.django_db(transaction=True)


def test_parallel_appraisals_for_same_owner_and_period_leave_one_complete_submission(monkeypatch):
    # HR-UC-006: two independent DB sessions must not bypass the duplicate guard.
    now = timezone.now()
    EmployeeServiceRecord.objects.create(
        user_id=10,
        department="CSE",
        designation_snapshot="Synthetic Staff",
    )
    HRPolicyVersion.objects.create(
        family="appraisal",
        version=1,
        effective_from=now - timedelta(days=1),
        parameters={
            "submission_window": {
                "start": (now - timedelta(hours=1)).isoformat(),
                "end": (now + timedelta(hours=1)).isoformat(),
            }
        },
        approved_by_user_id=99,
        approved_designation="hradmin",
    )
    actor = Principal(
        user_id=10,
        username="synthetic",
        display_name="Synthetic",
        kind="staff",
        active_role="staff",
        roles=("staff",),
        permissions=frozenset({"hreis.appraisal.create"}),
        modules=("hreis",),
    )
    original = service._persist

    def delayed_persist(*args, **kwargs):
        row = original(*args, **kwargs)
        # Widen the real uncommitted interval before the detail becomes visible.
        sleep(0.15)
        return row

    monkeypatch.setattr(service, "_persist", delayed_persist)
    gate = Barrier(2)

    def submit(index):
        close_old_connections()
        try:
            gate.wait(timeout=15)
            return service.submit_appraisal(
                actor,
                period_key="FY2026",
                submitted_form={"summary": "Synthetic"},
                idempotency_key=f"concurrent-appraisal-{index}",
            )
        except ConflictError as error:
            return error
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        outcomes = list(pool.map(submit, (0, 1)))
    assert sum(isinstance(row, HRRequest) for row in outcomes) == 1
    refused = [row for row in outcomes if isinstance(row, ConflictError)]
    assert len(refused) == 1 and refused[0].code == "appraisal_already_submitted"
    assert HRRequest.objects.filter(family="appraisal", user_id=10).count() == 1
    assert AppraisalDetail.objects.filter(period_key="FY2026").count() == 1
    assert AuditEvent.objects.filter(action="appraisal_submit").count() == 1
    assert Notification.objects.count() == OutboxEvent.objects.count() == 1

    original_detail = AppraisalDetail.objects.get()
    other_request = HRRequest.objects.create(user_id=10, family="appraisal", state="submitted")
    with (
        pytest.raises(IntegrityError, match="hr_appraisal_record_period_unique"),
        transaction.atomic(),
    ):
        AppraisalDetail.objects.create(
            request=other_request,
            employee_record=original_detail.employee_record,
            period_key=original_detail.period_key,
            submitted_form={"summary": "Duplicate"},
        )
