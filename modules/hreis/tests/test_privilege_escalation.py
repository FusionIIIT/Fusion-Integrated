"""Tests ensuring non-privileged roles cannot escalate or access restricted HR actions."""
import pytest
from rest_framework.test import APIClient

from conftest import make_session

pytestmark = pytest.mark.django_db


def test_student_cannot_access_hr_endpoints(stub_iam, user_ref):
    stub_iam(
        make_session(
            user_id=1001,
            kind="student",
            roles=("student",),
            modules=("placement_cell",),
            permissions=(),
        ),
        users={1001: user_ref(1001, name="Student Bob", kind="student")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    # Accessing personal service record
    resp = client.get("/api/v1/hreis/service-records/me/")
    assert resp.status_code == 403

    # Applying for leave
    resp_leave = client.post(
        "/api/v1/hreis/leaves/",
        {"leave_type": "casual", "start_date": "2026-03-01", "end_date": "2026-03-02", "duration_days": 1.0, "justification": "Rest"},
        format="json",
    )
    assert resp_leave.status_code == 403

    # Accessing stats
    resp_stats = client.get("/api/v1/hreis/stats/")
    assert resp_stats.status_code == 403


def test_regular_employee_cannot_verify_claims(stub_iam, user_ref):
    stub_iam(
        make_session(
            user_id=101,
            kind="faculty",
            roles=("faculty",),
            modules=("hr_eis",),
            permissions=("hr_eis.service_record.view_self", "hr_eis.ltc.apply", "hr_eis.ltc.view_self"),
        ),
        users={101: user_ref(101, name="Dr. Faculty", kind="faculty")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    # Attempt to verify LTC claim
    resp = client.post(
        "/api/v1/hreis/ltc/1/verify/",
        {"verdict": "verified", "remarks": "I verify my own"},
        format="json",
    )
    assert resp.status_code == 403


def test_accountant_cannot_modify_workflow_configurations(stub_iam, user_ref):
    stub_iam(
        make_session(
            user_id=801,
            kind="staff",
            roles=("accountant",),
            modules=("hr_eis",),
            permissions=("hr_eis.ltc.settle", "hr_eis.cpda.settle"),
        ),
        users={801: user_ref(801, name="Accountant", kind="staff")},
    )

    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION="Token fake-token")

    resp = client.post(
        "/api/v1/hreis/workflows/settings/",
        {"setting_key": "appraisal_window", "setting_value": {"active": True}},
        format="json",
    )
    assert resp.status_code == 403
