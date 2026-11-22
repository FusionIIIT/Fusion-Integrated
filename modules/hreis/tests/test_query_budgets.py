"""Query counts for the HR-EIS list endpoints, ensuring no N+1 query leaks.

The budget is per request: adding rows should not grow query count.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from conftest import make_session
from modules.hreis.models import (
    AppraisalSubmission,
    CpdaRequest,
    EmployeeServiceRecord,
    HrAuditLog,
    HrNotification,
    LeaveRequest,
    LtcRequest,
)

pytestmark = pytest.mark.django_db

HR_ADMIN_PERMS = (
    "hr_eis.service_record.view_self",
    "hr_eis.service_record.manage",
    "hr_eis.service_record.view_all",
    "hr_eis.leave.apply",
    "hr_eis.leave.view_self",
    "hr_eis.leave.review",
    "hr_eis.appraisal.submit",
    "hr_eis.appraisal.view_self",
    "hr_eis.appraisal.assign_reviewer",
    "hr_eis.appraisal.review",
    "hr_eis.appraisal.finalize",
    "hr_eis.ltc.apply",
    "hr_eis.ltc.view_self",
    "hr_eis.ltc.verify",
    "hr_eis.ltc.approve",
    "hr_eis.ltc.settle",
    "hr_eis.cpda.apply",
    "hr_eis.cpda.view_self",
    "hr_eis.cpda.verify",
    "hr_eis.cpda.approve",
    "hr_eis.cpda.settle",
    "hr_eis.workflow.configure",
    "hr_eis.audit.view",
    "hr_eis.notification.view_self",
)


def _client(stub_iam, permissions=HR_ADMIN_PERMS, uid=201, role="hr_admin"):
    stub_iam(
        make_session(
            user_id=uid,
            kind="faculty",
            permissions=permissions,
            modules=("hr_eis",),
            roles=(role,),
            active_role=role,
        )
    )
    c = APIClient()
    c.credentials(HTTP_AUTHORIZATION="Token mock-hr-admin")
    return c


@pytest.fixture
def hreis_cohort():
    """Seed sample data for each list endpoint."""
    records = []
    for i in range(5):
        uid = 300 + i
        EmployeeServiceRecord.objects.create(
            user_id=uid,
            employee_id=f"EMP{uid}",
            department="CSE",
            designation="Professor",
            category="faculty",
            leave_balances={"casual": 10},
        )
        LeaveRequest.objects.create(
            user_id=uid,
            leave_type="casual",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 3),
            duration_days=Decimal("2.0"),
            justification="Conference",
            status="pending",
        )
        AppraisalSubmission.objects.create(
            user_id=uid,
            academic_year="2025-2026",
            status="submitted",
        )
        LtcRequest.objects.create(
            user_id=uid,
            request_type="advance",
            block_year="2022-2025",
            travel_from="Jabalpur",
            travel_to="Delhi",
            travel_start_date=date(2026, 5, 1),
            travel_end_date=date(2026, 5, 5),
            estimated_amount=Decimal("15000.00"),
            status="submitted",
        )
        CpdaRequest.objects.create(
            user_id=uid,
            request_type="advance",
            purpose=f"Research papers {i}",
            amount=Decimal("20000.00"),
            status="submitted",
        )
        HrAuditLog.objects.create(
            actor_id=uid,
            actor_username=f"user{uid}",
            actor_role="faculty",
            action="submit_request",
            entity_type="leave_request",
            entity_id=str(uid),
        )
        HrNotification.objects.create(
            user_id=uid,
            title=f"Notification {i}",
            message="Test message",
            category="reminder",
        )
        records.append(uid)
    return records


@pytest.mark.parametrize(
    ("path", "budget"),
    [
        ("/api/v1/hreis/leaves/", 5),
        ("/api/v1/hreis/appraisals/", 5),
        ("/api/v1/hreis/ltc/", 5),
        ("/api/v1/hreis/cpda/", 5),
        ("/api/v1/hreis/audit-logs/", 5),
        ("/api/v1/hreis/notifications/", 5),
    ],
)
def test_hreis_list_endpoints_within_budget(
    stub_iam, hreis_cohort, django_assert_max_num_queries, path, budget
):
    client = _client(stub_iam)
    with django_assert_max_num_queries(budget):
        resp = client.get(path)
        assert resp.status_code == 200


def test_leaves_query_count_does_not_grow_with_rows(stub_iam, hreis_cohort):
    """Ensure adding more rows does not cause an N+1 query regression."""
    client = _client(stub_iam)

    from django.db import connection
    from django.test.utils import CaptureQueriesContext

    with CaptureQueriesContext(connection) as first:
        client.get("/api/v1/hreis/leaves/")

    for i in range(5, 10):
        uid = 300 + i
        LeaveRequest.objects.create(
            user_id=uid,
            leave_type="casual",
            start_date=date(2026, 4, 1),
            end_date=date(2026, 4, 3),
            duration_days=Decimal("2.0"),
            justification="Another trip",
            status="pending",
        )

    with CaptureQueriesContext(connection) as second:
        client.get("/api/v1/hreis/leaves/")

    assert len(second) == len(first), (
        f"{len(first)} queries for 5 rows, {len(second)} for 10 rows: N+1 detected"
    )
